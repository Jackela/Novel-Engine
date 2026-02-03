"""
Knowledge Management API

FastAPI routes for knowledge entry CRUD operations (Admin API).

Constitution Compliance:
- Article II (Hexagonal): API layer adapter for knowledge management use cases
- Article VII (Observability): Structured logging, metrics, tracing for all endpoints
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.security.auth_system import User, UserRole, require_role
from src.core.types.shared_types import CharacterId, KnowledgeEntryId, UserId

logger = structlog.get_logger(__name__)

# OpenTelemetry tracing (Article VII - Observability)
try:
    from opentelemetry import trace

    OTEL_AVAILABLE = True
    tracer = trace.get_tracer("novel_engine.knowledge_api")
except ImportError:
    OTEL_AVAILABLE = False
    tracer = None

from src.contexts.knowledge.application.ports.i_event_publisher import IEventPublisher
from src.contexts.knowledge.application.ports.i_knowledge_repository import (
    IKnowledgeRepository,
)
from src.contexts.knowledge.application.use_cases.create_knowledge_entry import (
    CreateKnowledgeEntryUseCase,
)
from src.contexts.knowledge.application.use_cases.delete_knowledge_entry import (
    DeleteKnowledgeEntryUseCase,
)
from src.contexts.knowledge.application.use_cases.migrate_markdown_files import (
    MigrateMarkdownFilesUseCase,
)
from src.contexts.knowledge.application.use_cases.update_knowledge_entry import (
    UpdateKnowledgeEntryUseCase,
)
from src.contexts.knowledge.domain.models.knowledge_entry import KnowledgeEntry
from src.contexts.knowledge.domain.models.access_level import AccessLevel
from src.contexts.knowledge.domain.models.knowledge_type import KnowledgeType
from src.contexts.knowledge.domain.models.agent_identity import AgentIdentity
from src.contexts.knowledge.infrastructure.adapters.markdown_migration_adapter import (
    MarkdownMigrationAdapter,
)
from src.contexts.knowledge.infrastructure.events.kafka_event_publisher import (
    KafkaEventPublisher,
)
from src.contexts.knowledge.infrastructure.repositories.postgresql_knowledge_repository import (
    PostgreSQLKnowledgeRepository,
)

# Request/Response Models


class CreateKnowledgeEntryRequest(BaseModel):
    """Request model for creating a knowledge entry."""

    content: str = Field(..., description="Knowledge content text")
    knowledge_type: str = Field(..., description="Category of knowledge")
    owning_character_id: Optional[CharacterId] = Field(
        None, description="Character this belongs to (None for world knowledge)"
    )
    access_level: str = Field(..., description="Access control level")
    allowed_roles: List[str] = Field(
        default_factory=list, description="Roles permitted (for ROLE_BASED access)"
    )
    allowed_character_ids: List[CharacterId] = Field(
        default_factory=list,
        description="Character IDs permitted (for CHARACTER_SPECIFIC)",
    )


class CreateKnowledgeEntryResponse(BaseModel):
    """Response model for creating a knowledge entry."""

    entry_id: KnowledgeEntryId = Field(
        ..., description="Unique identifier of created entry"
    )
    content: str
    knowledge_type: str
    owning_character_id: Optional[CharacterId]
    access_level: str
    allowed_roles: List[str]
    allowed_character_ids: List[CharacterId]
    created_at: str
    updated_at: str
    created_by: UserId


class UpdateKnowledgeEntryRequest(BaseModel):
    """Request model for updating a knowledge entry."""

    content: str = Field(..., description="New knowledge content text")


class KnowledgeEntryResponse(BaseModel):
    """Response model for knowledge entry details."""

    entry_id: KnowledgeEntryId
    content: str
    knowledge_type: str
    owning_character_id: Optional[CharacterId]
    access_level: str
    allowed_roles: List[str]
    allowed_character_ids: List[CharacterId]
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    created_by: UserId


def _parse_knowledge_type(value: str) -> KnowledgeType:
    try:
        return KnowledgeType(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _parse_access_level(value: str) -> AccessLevel:
    try:
        return AccessLevel(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _entry_to_response(entry: KnowledgeEntry) -> KnowledgeEntryResponse:
    return KnowledgeEntryResponse(
        entry_id=entry.id,
        content=entry.content,
        knowledge_type=entry.knowledge_type.value,
        owning_character_id=entry.owning_character_id,
        access_level=entry.access_control.access_level.value,
        allowed_roles=list(entry.access_control.allowed_roles),
        allowed_character_ids=list(entry.access_control.allowed_character_ids),
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
        created_by=entry.created_by,
    )


# Dependency injection helpers


async def get_repository() -> IKnowledgeRepository:
    """
    Get knowledge repository instance (dependency injection).

    NOTE: Current implementation uses direct async session creation.
    Future enhancement: Integrate with DatabaseManager singleton for centralized session management.
    """
    from core_platform.persistence.database import get_async_db_session

    async with get_async_db_session() as session:
        yield PostgreSQLKnowledgeRepository(session)


async def get_event_publisher() -> IEventPublisher:
    """
    Get event publisher instance (dependency injection).

    NOTE: Current implementation creates new KafkaClient instance per request.
    Future enhancement: Integrate with KafkaClient singleton for connection pooling.
    """
    from src.contexts.orchestration.infrastructure.kafka.kafka_client import KafkaClient

    kafka_client = KafkaClient()
    yield KafkaEventPublisher(kafka_client)


# Authentication integrated via SecurityService (T008, T043)
# Use require_role(UserRole.ADMIN) dependency in endpoints


# API Router


def create_knowledge_api() -> APIRouter:
    """
    Create Knowledge Management API router.

    Provides Admin API endpoints for:
    - POST /api/knowledge/entries (FR-002)
    - GET /api/knowledge/entries
    - GET /api/knowledge/entries/{id}
    - PUT /api/knowledge/entries/{id} (FR-003)
    - DELETE /api/knowledge/entries/{id} (FR-004)

    Constitution Compliance:
    - Article II (Hexagonal): API adapter for use cases
    - Article VII (Observability): All endpoints logged and instrumented

    Returns:
        APIRouter with knowledge management endpoints
    """
    router = APIRouter(
        prefix="/api/knowledge",
        tags=["Knowledge Management"],
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden - requires admin or game_master role"},
            500: {"description": "Internal server error"},
        },
    )

    @router.post(
        "/entries",
        response_model=CreateKnowledgeEntryResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create Knowledge Entry",
        description="Create a new knowledge entry with specified access control (FR-002)",
    )
    async def create_entry(
        request: CreateKnowledgeEntryRequest,
        repository: IKnowledgeRepository = Depends(get_repository),
        event_publisher: IEventPublisher = Depends(get_event_publisher),
        current_user: User = Depends(require_role(UserRole.ADMIN)),
    ) -> CreateKnowledgeEntryResponse:
        """
        Create a new knowledge entry.

        Requires: Admin role (enforced by authentication T008, T043)
        """
        user_id = current_user.id

        # Start OpenTelemetry span (Article VII - Observability)
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span("knowledge.create_entry") as span:
                span.set_attribute("knowledge_type", request.knowledge_type.value)
                span.set_attribute("access_level", request.access_level.value)
                span.set_attribute("user_id", user_id)

                try:
                    use_case = CreateKnowledgeEntryUseCase(repository, event_publisher)
                    entry_id = await use_case.execute(
                        content=request.content,
                        knowledge_type=request.knowledge_type,
                        owning_character_id=request.owning_character_id,
                        access_level=request.access_level,
                        created_by=user_id,
                        allowed_roles=tuple(request.allowed_roles),
                        allowed_character_ids=tuple(request.allowed_character_ids),
                    )

                    span.set_attribute("entry_id", entry_id)
                    span.set_attribute("success", True)
                    return CreateKnowledgeEntryResponse(entry_id=entry_id)

                except ValueError as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                    )
                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Internal server error",
                    )
        else:
            # Fallback without tracing
            try:
                use_case = CreateKnowledgeEntryUseCase(repository, event_publisher)
                entry_id = await use_case.execute(
                    content=request.content,
                    knowledge_type=request.knowledge_type,
                    owning_character_id=request.owning_character_id,
                    access_level=request.access_level,
                    created_by=user_id,
                    allowed_roles=tuple(request.allowed_roles),
                    allowed_character_ids=tuple(request.allowed_character_ids),
                )
                return CreateKnowledgeEntryResponse(entry_id=entry_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error",
                )

    @router.get(
        "/entries",
        response_model=List[KnowledgeEntryResponse],
        summary="List Knowledge Entries",
        description="Retrieve all knowledge entries with optional filtering",
    )
    async def list_entries(
        knowledge_type: Optional[KnowledgeType] = None,
        owning_character_id: Optional[CharacterId] = None,
        repository: IKnowledgeRepository = Depends(get_repository),
        current_user: User = Depends(require_role(UserRole.ADMIN)),
    ) -> List[KnowledgeEntryResponse]:
        """
        List knowledge entries with optional filters.

        Requires: Admin role (enforced by authentication T008, T043)

        Admin users can access all knowledge entries regardless of access control.
        Filters:
            - knowledge_type: Filter by knowledge category
            - owning_character_id: Filter by character ownership
        """
        # Admin users bypass access control - use admin agent identity
        admin_agent = AgentIdentity(character_id="admin", roles=("admin",))

        # Build knowledge type filter list
        knowledge_types = [knowledge_type] if knowledge_type else None

        try:
            entries = await repository.retrieve_for_agent(
                agent=admin_agent,
                knowledge_types=knowledge_types,
                owning_character_id=owning_character_id,
            )
            return [_entry_to_response(entry) for entry in entries]
        except Exception as e:
            logger.error(
                "knowledge_list_error",
                error=str(e),
                error_type=type(e).__name__,
                user_id=current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve knowledge entries",
            )

    @router.get(
        "/entries/{entry_id}",
        response_model=KnowledgeEntryResponse,
        summary="Get Knowledge Entry",
        description="Retrieve a specific knowledge entry by ID",
    )
    async def get_entry(
        entry_id: UUID,
        repository: IKnowledgeRepository = Depends(get_repository),
        current_user: User = Depends(require_role(UserRole.ADMIN)),
    ) -> KnowledgeEntryResponse:
        """
        Get a knowledge entry by ID.

        Requires: Admin role (enforced by authentication T008, T043)
        """
        try:
            entry = await repository.get_by_id(str(entry_id))

            if entry is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Knowledge entry not found",
                )

            # Use helper function to convert to response model
            return _entry_to_response(entry)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "knowledge_get_error",
                entry_id=str(entry_id),
                error=str(e),
                error_type=type(e).__name__,
                user_id=current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve knowledge entry",
            )

    @router.put(
        "/entries/{entry_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Update Knowledge Entry",
        description="Update the content of an existing knowledge entry (FR-003)",
    )
    async def update_entry(
        entry_id: UUID,
        request: UpdateKnowledgeEntryRequest,
        repository: IKnowledgeRepository = Depends(get_repository),
        event_publisher: IEventPublisher = Depends(get_event_publisher),
        current_user: User = Depends(require_role(UserRole.ADMIN)),
    ):
        """
        Update a knowledge entry's content.

        Requires: Admin role (enforced by authentication T008, T043)
        """
        user_id = current_user.id

        # Start OpenTelemetry span (Article VII - Observability)
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span("knowledge.update_entry") as span:
                span.set_attribute("entry_id", str(entry_id))
                span.set_attribute("user_id", user_id)

                try:
                    use_case = UpdateKnowledgeEntryUseCase(repository, event_publisher)
                    await use_case.execute(
                        entry_id=str(entry_id),
                        new_content=request.content,
                        updated_by=user_id,
                    )
                    span.set_attribute("success", True)

                except ValueError as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                    )
                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Internal server error",
                    )
        else:
            # Fallback without tracing
            try:
                use_case = UpdateKnowledgeEntryUseCase(repository, event_publisher)
                await use_case.execute(
                    entry_id=str(entry_id),
                    new_content=request.content,
                    updated_by=user_id,
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error",
                )

    @router.delete(
        "/entries/{entry_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete Knowledge Entry",
        description="Delete a knowledge entry (FR-004)",
    )
    async def delete_entry(
        entry_id: UUID,
        repository: IKnowledgeRepository = Depends(get_repository),
        event_publisher: IEventPublisher = Depends(get_event_publisher),
        current_user: User = Depends(require_role(UserRole.ADMIN)),
    ):
        """
        Delete a knowledge entry.

        Requires: Admin role (enforced by authentication T008, T043)
        """
        user_id = current_user.id

        # Start OpenTelemetry span (Article VII - Observability)
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span("knowledge.delete_entry") as span:
                span.set_attribute("entry_id", str(entry_id))
                span.set_attribute("user_id", user_id)

                try:
                    use_case = DeleteKnowledgeEntryUseCase(repository, event_publisher)
                    await use_case.execute(
                        entry_id=str(entry_id),
                        deleted_by=user_id,
                    )
                    span.set_attribute("success", True)

                except ValueError as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                    )
                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.set_attribute("success", False)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Internal server error",
                    )
        else:
            # Fallback without tracing
            try:
                use_case = DeleteKnowledgeEntryUseCase(repository, event_publisher)
                await use_case.execute(
                    entry_id=str(entry_id),
                    deleted_by=user_id,
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error",
                )

    # ===== Migration Endpoints (FR-016, FR-018) =====

    class MigrateMarkdownRequest(BaseModel):
        """Request model for Markdown migration."""

        markdown_directory: str = Field(
            ..., description="Root directory containing agent .md files"
        )
        create_backup: bool = Field(
            True, description="Create timestamped backup before migration"
        )

    class RollbackMigrationRequest(BaseModel):
        """Request model for migration rollback."""

        backup_path: str = Field(
            ..., description="Path to backup directory from migration"
        )

    class VerifyMigrationRequest(BaseModel):
        """Request model for migration verification."""

        markdown_directory: str = Field(
            ..., description="Root directory containing agent .md files"
        )

    @router.post(
        "/migrate",
        status_code=status.HTTP_200_OK,
        summary="Migrate Markdown files to knowledge base (FR-016)",
        dependencies=[Depends(require_role(UserRole.ADMIN))],
    )
    async def migrate_markdown_files(
        request: MigrateMarkdownRequest,
        repository: IKnowledgeRepository = Depends(get_repository),
    ):
        """
        Migrate all Markdown files to PostgreSQL knowledge base.

        Creates timestamped backup, parses Markdown files, creates knowledge entries.

        Functional Requirements:
            - FR-016: Manual migration from Markdown to knowledge base
            - FR-017: Timestamped backup creation

        Returns:
            Migration report with statistics and backup path
        """
        migration_adapter = MarkdownMigrationAdapter(repository=repository)
        use_case = MigrateMarkdownFilesUseCase(migration_adapter=migration_adapter)

        report = await use_case.execute(
            markdown_directory=request.markdown_directory,
            create_backup=request.create_backup,
        )

        return report

    @router.post(
        "/rollback",
        status_code=status.HTTP_200_OK,
        summary="Rollback migration to restore Markdown-based operation (FR-018)",
        dependencies=[Depends(require_role(UserRole.ADMIN))],
    )
    async def rollback_migration(
        request: RollbackMigrationRequest,
        repository: IKnowledgeRepository = Depends(get_repository),
    ):
        """
        Rollback migration by deleting entries and restoring Markdown files.

        Functional Requirements:
            - FR-018: Rollback capability to restore Markdown-based operation

        Returns:
            Rollback report with statistics
        """
        migration_adapter = MarkdownMigrationAdapter(repository=repository)
        use_case = MigrateMarkdownFilesUseCase(migration_adapter=migration_adapter)

        try:
            report = await use_case.rollback(backup_path=request.backup_path)
            return report
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post(
        "/verify",
        status_code=status.HTTP_200_OK,
        summary="Verify migration by comparing Markdown vs knowledge base (FR-019)",
        dependencies=[Depends(require_role(UserRole.ADMIN))],
    )
    async def verify_migration(
        request: VerifyMigrationRequest,
        repository: IKnowledgeRepository = Depends(get_repository),
    ):
        """
        Verify migration by comparing Markdown content vs PostgreSQL entries.

        Functional Requirements:
            - FR-019: Verification mode for comparing sources

        Returns:
            Verification report with comparison results
        """
        migration_adapter = MarkdownMigrationAdapter(repository=repository)
        use_case = MigrateMarkdownFilesUseCase(migration_adapter=migration_adapter)

        report = await use_case.verify(markdown_directory=request.markdown_directory)

        return report

    return router

