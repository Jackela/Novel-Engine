"""
Repository Patterns and Data Access Layer
========================================

Generic repository patterns and data access abstractions for Novel Engine platform.
"""

import logging
from abc import ABC
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query, Session

from ..monitoring.metrics import RepositoryMetrics
from .models import BaseModel, SoftDeleteModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RepositoryException(Exception):
    """Base exception for repository operations."""

    pass


class EntityNotFoundException(RepositoryException):
    """Raised when an entity is not found."""

    pass


class EntityAlreadyExistsException(RepositoryException):
    """Raised when attempting to create an entity that already exists."""

    pass


class RepositoryOperationException(RepositoryException):
    """Raised when a repository operation fails."""

    pass


class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository providing common CRUD operations.

    Features:
    - Generic CRUD operations
    - Pagination support
    - Filtering and sorting
    - Soft delete support
    - Transaction management
    - Performance monitoring
    """

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session
        self._metrics = RepositoryMetrics(model.__name__)

    # Create Operations

    def create(self, entity: T) -> T:
        """Create a new entity."""
        try:
            self._metrics.record_operation_start("create")

            # Validate entity before saving
            validation_errors = entity.validate()
            if validation_errors:
                raise RepositoryOperationException(f"Validation failed: {validation_errors}")

            self.session.add(entity)
            self.session.flush()  # Get the ID without committing
            self.session.refresh(entity)

            self._metrics.record_operation_success("create")
            logger.debug(f"Created {self.model.__name__} with id {entity.id}")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("create")
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to create entity: {e}")

    def create_many(self, entities: List[T]) -> List[T]:
        """Create multiple entities in a single transaction."""
        try:
            self._metrics.record_operation_start("create_many")

            # Validate all entities
            for entity in entities:
                validation_errors = entity.validate()
                if validation_errors:
                    raise RepositoryOperationException(
                        f"Validation failed for entity {entity}: {validation_errors}"
                    )

            self.session.add_all(entities)
            self.session.flush()

            # Refresh all entities to get generated IDs
            for entity in entities:
                self.session.refresh(entity)

            self._metrics.record_operation_success("create_many")
            logger.debug(f"Created {len(entities)} {self.model.__name__} entities")
            return entities

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("create_many")
            logger.error(f"Failed to create {self.model.__name__} entities: {e}")
            raise RepositoryOperationException(f"Failed to create entities: {e}")

    # Read Operations

    def get_by_id(self, entity_id: Union[UUID, str]) -> Optional[T]:
        """Get an entity by its ID."""
        try:
            self._metrics.record_operation_start("get_by_id")

            query = self._build_base_query()
            entity = query.filter(self.model.id == entity_id).first()

            self._metrics.record_operation_success("get_by_id")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("get_by_id")
            logger.error(f"Failed to get {self.model.__name__} by id {entity_id}: {e}")
            raise RepositoryOperationException(f"Failed to get entity: {e}")

    def get_by_id_or_raise(self, entity_id: Union[UUID, str]) -> T:
        """Get an entity by ID or raise EntityNotFoundException."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFoundException(f"{self.model.__name__} with id {entity_id} not found")
        return entity

    def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[T]:
        """Get all entities with pagination."""
        try:
            self._metrics.record_operation_start("get_all")

            query = self._build_base_query()
            query = self._apply_ordering(query, order_by, order_direction)
            query = query.offset(offset).limit(limit)

            entities = query.all()

            self._metrics.record_operation_success("get_all")
            return entities

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("get_all")
            logger.error(f"Failed to get all {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to get entities: {e}")

    def find_by(self, **filters) -> List[T]:
        """Find entities by arbitrary filters."""
        try:
            self._metrics.record_operation_start("find_by")

            query = self._build_base_query()
            query = self._apply_filters(query, filters)

            entities = query.all()

            self._metrics.record_operation_success("find_by")
            return entities

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("find_by")
            logger.error(f"Failed to find {self.model.__name__} by filters {filters}: {e}")
            raise RepositoryOperationException(f"Failed to find entities: {e}")

    def find_one_by(self, **filters) -> Optional[T]:
        """Find a single entity by filters."""
        try:
            self._metrics.record_operation_start("find_one_by")

            query = self._build_base_query()
            query = self._apply_filters(query, filters)

            entity = query.first()

            self._metrics.record_operation_success("find_one_by")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("find_one_by")
            logger.error(f"Failed to find one {self.model.__name__} by filters {filters}: {e}")
            raise RepositoryOperationException(f"Failed to find entity: {e}")

    def count(self, **filters) -> int:
        """Count entities matching filters."""
        try:
            self._metrics.record_operation_start("count")

            query = self._build_base_query()
            query = self._apply_filters(query, filters)

            count = query.count()

            self._metrics.record_operation_success("count")
            return count

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("count")
            logger.error(f"Failed to count {self.model.__name__} with filters {filters}: {e}")
            raise RepositoryOperationException(f"Failed to count entities: {e}")

    def exists(self, **filters) -> bool:
        """Check if entities exist matching filters."""
        try:
            self._metrics.record_operation_start("exists")

            query = self._build_base_query()
            query = self._apply_filters(query, filters)

            exists = query.first() is not None

            self._metrics.record_operation_success("exists")
            return exists

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("exists")
            logger.error(
                f"Failed to check existence of {self.model.__name__} with filters {filters}: {e}"
            )
            raise RepositoryOperationException(f"Failed to check entity existence: {e}")

    # Update Operations

    def update(self, entity: T) -> T:
        """Update an existing entity."""
        try:
            self._metrics.record_operation_start("update")

            # Validate entity before updating
            validation_errors = entity.validate()
            if validation_errors:
                raise RepositoryOperationException(f"Validation failed: {validation_errors}")

            # Make sure the entity is attached to the session
            if entity not in self.session:
                entity = self.session.merge(entity)

            self.session.flush()
            self.session.refresh(entity)

            self._metrics.record_operation_success("update")
            logger.debug(f"Updated {self.model.__name__} with id {entity.id}")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("update")
            logger.error(f"Failed to update {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to update entity: {e}")

    def update_by_id(self, entity_id: Union[UUID, str], **updates) -> Optional[T]:
        """Update an entity by ID with given field updates."""
        try:
            self._metrics.record_operation_start("update_by_id")

            entity = self.get_by_id(entity_id)
            if entity is None:
                return None

            entity.update(**updates)
            return self.update(entity)

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("update_by_id")
            logger.error(f"Failed to update {self.model.__name__} by id {entity_id}: {e}")
            raise RepositoryOperationException(f"Failed to update entity: {e}")

    # Delete Operations

    def delete(self, entity: T) -> bool:
        """Delete an entity (hard delete or soft delete based on model)."""
        try:
            self._metrics.record_operation_start("delete")

            if isinstance(entity, SoftDeleteModel):
                entity.soft_delete()
                self.session.flush()
            else:
                self.session.delete(entity)
                self.session.flush()

            self._metrics.record_operation_success("delete")
            logger.debug(f"Deleted {self.model.__name__} with id {entity.id}")
            return True

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("delete")
            logger.error(f"Failed to delete {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to delete entity: {e}")

    def delete_by_id(self, entity_id: Union[UUID, str]) -> bool:
        """Delete an entity by ID."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False

        return self.delete(entity)

    def delete_many(self, **filters) -> int:
        """Delete multiple entities matching filters."""
        try:
            self._metrics.record_operation_start("delete_many")

            query = self._build_base_query()
            query = self._apply_filters(query, filters)

            if issubclass(self.model, SoftDeleteModel):
                # Soft delete: update is_deleted flag
                count = query.update(
                    {self.model.is_deleted: True, self.model.deleted_at: func.now()}
                )
            else:
                # Hard delete
                count = query.delete()

            self.session.flush()

            self._metrics.record_operation_success("delete_many")
            logger.debug(f"Deleted {count} {self.model.__name__} entities")
            return count

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("delete_many")
            logger.error(
                f"Failed to delete {self.model.__name__} entities with filters {filters}: {e}"
            )
            raise RepositoryOperationException(f"Failed to delete entities: {e}")

    # Helper Methods

    def _build_base_query(self) -> Query:
        """Build the base query, excluding soft-deleted items if applicable."""
        query = self.session.query(self.model)

        if issubclass(self.model, SoftDeleteModel):
            query = query.filter(self.model.is_deleted is False)

        return query

    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply filters to a query."""
        for key, value in filters.items():
            if hasattr(self.model, key):
                if isinstance(value, list):
                    query = query.filter(getattr(self.model, key).in_(value))
                else:
                    query = query.filter(getattr(self.model, key) == value)

        return query

    def _apply_ordering(self, query: Query, order_by: str, order_direction: str) -> Query:
        """Apply ordering to a query."""
        if hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(asc(column))

        return query

    def get_metrics(self) -> Dict[str, Any]:
        """Get repository performance metrics."""
        return self._metrics.get_all_metrics()


class AsyncBaseRepository(Generic[T], ABC):
    """
    Asynchronous base repository for async operations.

    Similar to BaseRepository but designed for async/await patterns.
    """

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
        self._metrics = RepositoryMetrics(f"Async{model.__name__}")

    async def create(self, entity: T) -> T:
        """Create a new entity asynchronously."""
        try:
            self._metrics.record_operation_start("create")

            validation_errors = entity.validate()
            if validation_errors:
                raise RepositoryOperationException(f"Validation failed: {validation_errors}")

            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)

            self._metrics.record_operation_success("create")
            logger.debug(f"Created {self.model.__name__} with id {entity.id}")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("create")
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to create entity: {e}")

    async def get_by_id(self, entity_id: Union[UUID, str]) -> Optional[T]:
        """Get an entity by its ID asynchronously."""
        try:
            self._metrics.record_operation_start("get_by_id")

            stmt = select(self.model).where(self.model.id == entity_id)
            if issubclass(self.model, SoftDeleteModel):
                stmt = stmt.where(self.model.is_deleted is False)

            result = await self.session.execute(stmt)
            entity = result.scalar_one_or_none()

            self._metrics.record_operation_success("get_by_id")
            return entity

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("get_by_id")
            logger.error(f"Failed to get {self.model.__name__} by id {entity_id}: {e}")
            raise RepositoryOperationException(f"Failed to get entity: {e}")

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[T]:
        """Get all entities with pagination asynchronously."""
        try:
            self._metrics.record_operation_start("get_all")

            stmt = select(self.model)
            if issubclass(self.model, SoftDeleteModel):
                stmt = stmt.where(self.model.is_deleted is False)

            # Apply ordering
            if hasattr(self.model, order_by):
                column = getattr(self.model, order_by)
                if order_direction.lower() == "desc":
                    stmt = stmt.order_by(desc(column))
                else:
                    stmt = stmt.order_by(asc(column))

            stmt = stmt.offset(offset).limit(limit)

            result = await self.session.execute(stmt)
            entities = result.scalars().all()

            self._metrics.record_operation_success("get_all")
            return list(entities)

        except SQLAlchemyError as e:
            self._metrics.record_operation_error("get_all")
            logger.error(f"Failed to get all {self.model.__name__}: {e}")
            raise RepositoryOperationException(f"Failed to get entities: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get repository performance metrics."""
        return self._metrics.get_all_metrics()


# Factory function for creating repositories
def create_repository(model: Type[T], session: Session) -> BaseRepository[T]:
    """Factory function to create a repository for a given model."""
    return BaseRepository(model, session)


def create_async_repository(model: Type[T], session: AsyncSession) -> AsyncBaseRepository[T]:
    """Factory function to create an async repository for a given model."""
    return AsyncBaseRepository(model, session)
