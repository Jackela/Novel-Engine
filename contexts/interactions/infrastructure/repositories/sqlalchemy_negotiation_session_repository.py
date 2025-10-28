#!/usr/bin/env python3
"""
SQLAlchemy Implementation of NegotiationSessionRepository

This module provides the concrete implementation of the NegotiationSessionRepository
interface using SQLAlchemy ORM for persistence operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.aggregates.negotiation_session import NegotiationSession

# Import domain interfaces and objects
from ....domain.repositories.negotiation_session_repository import (
    NegotiationSessionRepository,
)
from ....domain.value_objects.interaction_id import InteractionId

# Import infrastructure models
from ..persistence.models.negotiation_session_model import NegotiationSessionModel

logger = logging.getLogger(__name__)


class SQLAlchemyNegotiationSessionRepository(NegotiationSessionRepository):
    """
    SQLAlchemy-based implementation of the NegotiationSessionRepository.

    Provides persistence operations for NegotiationSession aggregates using
    SQLAlchemy ORM and async database operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def save(self, session: NegotiationSession) -> None:
        """
        Save or update a negotiation session.

        Args:
            session: The NegotiationSession aggregate to persist

        Raises:
            IntegrityError: If there are database constraint violations
            OptimisticLockError: If the session was modified by another process
        """
        try:
            # Check if session already exists
            existing = await self.session.get(
                NegotiationSessionModel, session.session_id.value
            )

            if existing:
                # Update existing session
                existing.update_from_domain_entity(session)
                logger.info(f"Updated negotiation session {session.session_id}")
            else:
                # Create new session
                model = NegotiationSessionModel.from_domain_entity(session)
                self.session.add(model)
                logger.info(f"Created new negotiation session {session.session_id}")

            await self.session.flush()

        except IntegrityError as e:
            logger.error(
                f"Integrity error saving negotiation session {session.session_id}: {e}"
            )
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error saving negotiation session {session.session_id}: {e}")
            await self.session.rollback()
            raise

    async def get_by_id(
        self, session_id: InteractionId
    ) -> Optional[NegotiationSession]:
        """
        Retrieve a negotiation session by its unique identifier.

        Args:
            session_id: The unique identifier for the session

        Returns:
            The NegotiationSession if found, None otherwise
        """
        try:
            model = await self.session.get(NegotiationSessionModel, session_id.value)

            if model:
                return model.to_domain_entity()
            return None

        except Exception as e:
            logger.error(f"Error retrieving negotiation session {session_id}: {e}")
            raise

    async def find_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[NegotiationSession]:
        """
        Find negotiation sessions matching the specified filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order results by
            order_direction: Sort direction (asc/desc)

        Returns:
            List of matching NegotiationSession objects
        """
        try:
            # Build base query
            query = select(NegotiationSessionModel)

            # Apply filters
            conditions = []

            if "created_by" in filters:
                conditions.append(
                    NegotiationSessionModel.created_by == filters["created_by"]
                )

            if "session_type" in filters:
                conditions.append(
                    NegotiationSessionModel.session_type == filters["session_type"]
                )

            if "negotiation_domain" in filters:
                conditions.append(
                    NegotiationSessionModel.negotiation_domain
                    == filters["negotiation_domain"]
                )

            if "priority_level" in filters:
                conditions.append(
                    NegotiationSessionModel.priority_level == filters["priority_level"]
                )

            if "confidentiality_level" in filters:
                conditions.append(
                    NegotiationSessionModel.confidentiality_level
                    == filters["confidentiality_level"]
                )

            # Date range filters
            if "created_after" in filters:
                conditions.append(
                    NegotiationSessionModel.created_at >= filters["created_after"]
                )

            if "created_before" in filters:
                conditions.append(
                    NegotiationSessionModel.created_at <= filters["created_before"]
                )

            if "updated_after" in filters:
                conditions.append(
                    NegotiationSessionModel.updated_at >= filters["updated_after"]
                )

            if "updated_before" in filters:
                conditions.append(
                    NegotiationSessionModel.updated_at <= filters["updated_before"]
                )

            # Numeric range filters
            if "min_parties" in filters:
                conditions.append(
                    NegotiationSessionModel.total_parties >= filters["min_parties"]
                )

            if "max_parties" in filters:
                conditions.append(
                    NegotiationSessionModel.total_parties <= filters["max_parties"]
                )

            if "min_proposals" in filters:
                conditions.append(
                    NegotiationSessionModel.total_proposals >= filters["min_proposals"]
                )

            # Status-based filters (using JSON path queries for PostgreSQL)
            if "is_active" in filters:
                conditions.append(
                    text("status->>'is_active' = :is_active").bindparam(
                        is_active=str(filters["is_active"]).lower()
                    )
                )

            if "phase" in filters:
                conditions.append(
                    text("status->>'phase' = :phase").bindparam(phase=filters["phase"])
                )

            if "outcome" in filters:
                conditions.append(
                    text("status->>'outcome' = :outcome").bindparam(
                        outcome=filters["outcome"]
                    )
                )

            # Apply all conditions
            if conditions:
                query = query.where(and_(*conditions))

            # Apply ordering
            order_column = getattr(
                NegotiationSessionModel, order_by, NegotiationSessionModel.created_at
            )
            if order_direction.lower() == "asc":
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute query
            result = await self.session.execute(query)
            models = result.scalars().all()

            # Convert to domain entities
            return [model.to_domain_entity() for model in models]

        except Exception as e:
            logger.error(
                f"Error finding negotiation sessions with filters {filters}: {e}"
            )
            raise

    async def find_by_created_by(self, created_by: UUID) -> List[NegotiationSession]:
        """
        Find all negotiation sessions created by a specific user.

        Args:
            created_by: UUID of the user who created the sessions

        Returns:
            List of NegotiationSession objects created by the user
        """
        return await self.find_by_filters({"created_by": created_by})

    async def find_by_participant(
        self, participant_id: UUID
    ) -> List[NegotiationSession]:
        """
        Find all negotiation sessions where the specified entity is a participant.

        Args:
            participant_id: UUID of the participating entity

        Returns:
            List of NegotiationSession objects with the participant
        """
        try:
            # Use JSON query to search for participant in parties
            query = (
                select(NegotiationSessionModel)
                .where(
                    text("parties ? :participant_id").bindparam(
                        participant_id=str(participant_id)
                    )
                )
                .order_by(desc(NegotiationSessionModel.created_at))
            )

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [model.to_domain_entity() for model in models]

        except Exception as e:
            logger.error(
                f"Error finding sessions for participant {participant_id}: {e}"
            )
            raise

    async def find_active_sessions(self) -> List[NegotiationSession]:
        """
        Find all currently active negotiation sessions.

        Returns:
            List of active NegotiationSession objects
        """
        try:
            query = (
                select(NegotiationSessionModel)
                .where(text("status->>'is_active' = 'true'"))
                .order_by(desc(NegotiationSessionModel.updated_at))
            )

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [model.to_domain_entity() for model in models]

        except Exception as e:
            logger.error(f"Error finding active sessions: {e}")
            raise

    async def find_sessions_by_status(
        self, phase: Optional[str] = None, outcome: Optional[str] = None
    ) -> List[NegotiationSession]:
        """
        Find negotiation sessions by their status.

        Args:
            phase: Optional phase filter
            outcome: Optional outcome filter

        Returns:
            List of matching NegotiationSession objects
        """
        try:
            conditions = []

            if phase:
                conditions.append(
                    text("status->>'phase' = :phase").bindparam(phase=phase)
                )

            if outcome:
                conditions.append(
                    text("status->>'outcome' = :outcome").bindparam(outcome=outcome)
                )

            if not conditions:
                return []

            query = (
                select(NegotiationSessionModel)
                .where(and_(*conditions))
                .order_by(desc(NegotiationSessionModel.updated_at))
            )

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [model.to_domain_entity() for model in models]

        except Exception as e:
            logger.error(
                f"Error finding sessions by status (phase={phase}, outcome={outcome}): {e}"
            )
            raise

    async def find_sessions_by_domain(self, domain: str) -> List[NegotiationSession]:
        """
        Find negotiation sessions in a specific domain.

        Args:
            domain: The negotiation domain to filter by

        Returns:
            List of NegotiationSession objects in the domain
        """
        return await self.find_by_filters({"negotiation_domain": domain})

    async def find_sessions_by_type(
        self, session_type: str
    ) -> List[NegotiationSession]:
        """
        Find negotiation sessions of a specific type.

        Args:
            session_type: The session type to filter by

        Returns:
            List of NegotiationSession objects of the specified type
        """
        return await self.find_by_filters({"session_type": session_type})

    async def find_sessions_requiring_attention(
        self, hours_until_timeout: int = 24
    ) -> List[NegotiationSession]:
        """
        Find sessions that require attention (approaching timeout, stalled, etc.).

        Args:
            hours_until_timeout: Hours before timeout to consider "requiring attention"

        Returns:
            List of NegotiationSession objects requiring attention
        """
        try:
            cutoff_time = datetime.now(timezone.utc) + timedelta(
                hours=hours_until_timeout
            )
            stagnant_time = datetime.now(timezone.utc) - timedelta(
                hours=48
            )  # No activity for 2 days

            # Find sessions that are:
            # 1. Active but approaching timeout
            # 2. Active but haven't had recent activity
            # 3. Have been in the same phase too long
            query = (
                select(NegotiationSessionModel)
                .where(
                    and_(
                        text("status->>'is_active' = 'true'"),
                        or_(
                            # Approaching session timeout
                            func.date_part(
                                "epoch",
                                NegotiationSessionModel.created_at
                                + func.make_interval(
                                    hours=NegotiationSessionModel.session_timeout_hours
                                ),
                            )
                            <= func.date_part("epoch", cutoff_time),
                            # No recent activity
                            NegotiationSessionModel.updated_at <= stagnant_time,
                            # Too many parties without responses
                            and_(
                                NegotiationSessionModel.total_parties >= 3,
                                NegotiationSessionModel.total_responses
                                < NegotiationSessionModel.total_parties,
                            ),
                        ),
                    )
                )
                .order_by(asc(NegotiationSessionModel.updated_at))
            )

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [model.to_domain_entity() for model in models]

        except Exception as e:
            logger.error(f"Error finding sessions requiring attention: {e}")
            raise

    async def count_sessions_by_criteria(self, filters: Dict[str, Any]) -> int:
        """
        Count negotiation sessions matching the specified criteria.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            Number of sessions matching the criteria
        """
        try:
            # Build query similar to find_by_filters but count only
            query = select(func.count(NegotiationSessionModel.session_id))

            conditions = []

            if "created_by" in filters:
                conditions.append(
                    NegotiationSessionModel.created_by == filters["created_by"]
                )

            if "session_type" in filters:
                conditions.append(
                    NegotiationSessionModel.session_type == filters["session_type"]
                )

            if "negotiation_domain" in filters:
                conditions.append(
                    NegotiationSessionModel.negotiation_domain
                    == filters["negotiation_domain"]
                )

            if "is_active" in filters:
                conditions.append(
                    text("status->>'is_active' = :is_active").bindparam(
                        is_active=str(filters["is_active"]).lower()
                    )
                )

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting sessions with criteria {filters}: {e}")
            raise

    async def delete(self, session_id: InteractionId) -> bool:
        """
        Delete a negotiation session.

        Args:
            session_id: The unique identifier for the session to delete

        Returns:
            True if the session was deleted, False if not found
        """
        try:
            # Check if session exists first
            existing = await self.session.get(NegotiationSessionModel, session_id.value)
            if not existing:
                return False

            await self.session.delete(existing)
            await self.session.flush()

            logger.info(f"Deleted negotiation session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting negotiation session {session_id}: {e}")
            await self.session.rollback()
            raise

    async def exists(self, session_id: InteractionId) -> bool:
        """
        Check if a negotiation session exists.

        Args:
            session_id: The unique identifier for the session

        Returns:
            True if the session exists, False otherwise
        """
        try:
            query = select(func.count(NegotiationSessionModel.session_id)).where(
                NegotiationSessionModel.session_id == session_id.value
            )

            result = await self.session.execute(query)
            count = result.scalar() or 0

            return count > 0

        except Exception as e:
            logger.error(
                f"Error checking existence of negotiation session {session_id}: {e}"
            )
            raise

    async def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get statistical information about negotiation sessions.

        Returns:
            Dictionary containing session statistics
        """
        try:
            # Get basic counts
            total_query = select(func.count(NegotiationSessionModel.session_id))
            total_result = await self.session.execute(total_query)
            total_sessions = total_result.scalar() or 0

            # Get active sessions count
            active_query = select(func.count(NegotiationSessionModel.session_id)).where(
                text("status->>'is_active' = 'true'")
            )
            active_result = await self.session.execute(active_query)
            active_sessions = active_result.scalar() or 0

            # Get sessions by type
            type_query = select(
                NegotiationSessionModel.session_type,
                func.count(NegotiationSessionModel.session_id),
            ).group_by(NegotiationSessionModel.session_type)

            type_result = await self.session.execute(type_query)
            sessions_by_type = dict(type_result.fetchall())

            # Get sessions by priority
            priority_query = select(
                NegotiationSessionModel.priority_level,
                func.count(NegotiationSessionModel.session_id),
            ).group_by(NegotiationSessionModel.priority_level)

            priority_result = await self.session.execute(priority_query)
            sessions_by_priority = dict(priority_result.fetchall())

            # Get average statistics
            avg_query = select(
                func.avg(NegotiationSessionModel.total_parties).label("avg_parties"),
                func.avg(NegotiationSessionModel.total_proposals).label(
                    "avg_proposals"
                ),
                func.avg(NegotiationSessionModel.total_responses).label(
                    "avg_responses"
                ),
            )

            avg_result = await self.session.execute(avg_query)
            avg_stats = avg_result.first()

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "completed_sessions": total_sessions - active_sessions,
                "sessions_by_type": sessions_by_type,
                "sessions_by_priority": sessions_by_priority,
                "average_parties_per_session": float(avg_stats.avg_parties or 0),
                "average_proposals_per_session": float(avg_stats.avg_proposals or 0),
                "average_responses_per_session": float(avg_stats.avg_responses or 0),
                "generated_at": datetime.now(timezone.utc),
            }

        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            raise

    async def find_sessions_by_date_range(
        self, start_date, end_date, date_field: str = "created_at"
    ) -> List[NegotiationSession]:
        """
        Find sessions within a specific date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            date_field: Field to filter by (created_at, updated_at, etc.)

        Returns:
            List of NegotiationSession objects within the date range
        """
        filters = {}
        if date_field == "created_at":
            filters["created_after"] = start_date
            filters["created_before"] = end_date
        elif date_field == "updated_at":
            filters["updated_after"] = start_date
            filters["updated_before"] = end_date
        else:
            raise ValueError(f"Unsupported date field: {date_field}")

        return await self.find_by_filters(
            filters, limit=1000
        )  # Large limit for date ranges

    async def batch_update_sessions(
        self, session_updates: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Perform batch updates on multiple sessions.

        Args:
            session_updates: List of update operations with session IDs and changes

        Returns:
            List of session IDs that were successfully updated
        """
        updated_session_ids = []

        try:
            for update_data in session_updates:
                session_id = update_data.get("session_id")
                updates = update_data.get("updates", {})

                if not session_id or not updates:
                    continue

                # Build update statement
                stmt = (
                    update(NegotiationSessionModel)
                    .where(NegotiationSessionModel.session_id == UUID(session_id))
                    .values(**updates, updated_at=datetime.now(timezone.utc))
                )

                result = await self.session.execute(stmt)

                if result.rowcount > 0:
                    updated_session_ids.append(session_id)

            await self.session.flush()

            logger.info(f"Batch updated {len(updated_session_ids)} sessions")
            return updated_session_ids

        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            await self.session.rollback()
            raise
