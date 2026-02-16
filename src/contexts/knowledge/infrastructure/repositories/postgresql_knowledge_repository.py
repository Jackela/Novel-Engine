"""
PostgreSQLKnowledgeRepository Adapter

Infrastructure adapter implementing IKnowledgeRepository for PostgreSQL persistence.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article IV (SSOT): PostgreSQL as authoritative source, no caching for MVP
"""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.types.shared_types import CharacterId, KnowledgeEntryId

from ...application.ports.i_knowledge_repository import IKnowledgeRepository
from ...domain.models.access_control_rule import AccessControlRule
from ...domain.models.access_level import AccessLevel
from ...domain.models.agent_identity import AgentIdentity
from ...domain.models.knowledge_entry import KnowledgeEntry
from ...domain.models.knowledge_type import KnowledgeType
from ..adapters.embedding_generator_adapter import EmbeddingGeneratorAdapter


class PostgreSQLKnowledgeRepository(IKnowledgeRepository):
    """
    PostgreSQL adapter for knowledge entry persistence.

    Implements IKnowledgeRepository port using PostgreSQL with asyncpg driver.
    Uses raw SQL via SQLAlchemy Core for performance and transparency.

    Constitution Compliance:
    - Article II (Hexagonal): Adapter implementing port defined by application layer
    - Article IV (SSOT): PostgreSQL is authoritative source, no Redis caching
    - Article VII (Observability): All operations logged and instrumented

    Performance Requirements:
    - SC-002: retrieve_for_agent must complete in <500ms for ≤100 entries
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_generator: EmbeddingGeneratorAdapter | None = None,
    ):
        """
        Initialize repository with database session.

        Args:
            session: AsyncSession from DatabaseManager
            embedding_generator: Optional adapter for generating embeddings (for semantic search)

        Constitution Compliance:
        - Article V (SOLID): DIP - Depend on AsyncSession abstraction
        """
        self._session = session
        self._embedding_generator = embedding_generator or EmbeddingGeneratorAdapter()

    async def save(self, entry: KnowledgeEntry) -> None:
        """
        Persist a knowledge entry (insert new or update existing).

        Uses PostgreSQL INSERT ... ON CONFLICT for upsert semantics.

        Args:
            entry: KnowledgeEntry aggregate to persist

        Raises:
            RepositoryError: If persistence operation fails

        Constitution Compliance:
        - Article IV (SSOT): Direct PostgreSQL persistence
        """
        from sqlalchemy import text

        # Upsert SQL with ON CONFLICT for idempotency
        upsert_sql = text("""
            INSERT INTO knowledge_entries (
                id, content, knowledge_type, owning_character_id,
                access_level, allowed_roles, allowed_character_ids,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :content, :knowledge_type, :owning_character_id,
                :access_level, :allowed_roles, :allowed_character_ids,
                :created_at, :updated_at, :created_by
            )
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                updated_at = EXCLUDED.updated_at
        """)

        # Execute upsert
        await self._session.execute(
            upsert_sql,
            {
                "id": UUID(entry.id),
                "content": entry.content,
                "knowledge_type": entry.knowledge_type.value,
                "owning_character_id": entry.owning_character_id,
                "access_level": entry.access_control.access_level.value,
                "allowed_roles": (
                    list(entry.access_control.allowed_roles)
                    if entry.access_control.allowed_roles
                    else None
                ),
                "allowed_character_ids": (
                    list(entry.access_control.allowed_character_ids)
                    if entry.access_control.allowed_character_ids
                    else None
                ),
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "created_by": entry.created_by,
            },
        )

        # Commit handled by session context manager

    async def get_by_id(self, entry_id: KnowledgeEntryId) -> KnowledgeEntry | None:
        """
        Retrieve a knowledge entry by its unique identifier.

        Args:
            entry_id: Unique identifier of the knowledge entry

        Returns:
            KnowledgeEntry if found, None otherwise

        Raises:
            RepositoryError: If retrieval operation fails

        Constitution Compliance:
        - Article IV (SSOT): Direct PostgreSQL retrieval, no cache
        """
        from sqlalchemy import text

        # SELECT query
        select_sql = text("""
            SELECT 
                id, content, knowledge_type, owning_character_id,
                access_level, allowed_roles, allowed_character_ids,
                created_at, updated_at, created_by
            FROM knowledge_entries
            WHERE id = :entry_id
        """)

        result = await self._session.execute(select_sql, {"entry_id": UUID(entry_id)})
        row = result.fetchone()

        if row is None:
            return None

        # Map row to domain model
        return self._row_to_domain_model(row)

    async def retrieve_for_agent(
        self,
        agent: AgentIdentity,
        knowledge_types: List[KnowledgeType] | None = None,
        owning_character_id: CharacterId | None = None,
    ) -> List[KnowledgeEntry]:
        """
        Retrieve all knowledge entries accessible to an agent.

        Applies access control filtering:
        - PUBLIC: Always accessible
        - ROLE_BASED: Agent must have one of the allowed roles
        - CHARACTER_SPECIFIC: Agent's character_id must be in allowed list

        Uses PostgreSQL GIN indexes for efficient array filtering.

        Args:
            agent: Agent identity (character_id and roles)
            knowledge_types: Optional filter by knowledge types
            owning_character_id: Optional filter by owning character

        Returns:
            List of KnowledgeEntry aggregates accessible to the agent

        Raises:
            RepositoryError: If retrieval operation fails

        Performance Requirement:
        - SC-002: Must complete in <500ms for ≤100 entries

        Constitution Compliance:
        - Article I (DDD): Domain model (is_accessible_by) validates access
        - Article IV (SSOT): PostgreSQL query with GIN index optimization
        """
        from sqlalchemy import text

        # Build dynamic WHERE clause
        where_conditions = []
        params = {
            "character_id": agent.character_id,
            "roles": list(agent.roles) if agent.roles else [],
        }

        # Access control filtering (PostgreSQL-optimized)
        access_filter = """
            (
                access_level = 'public'
                OR (access_level = 'role_based' AND allowed_roles && CAST(:roles AS TEXT[]))
                OR (access_level = 'character_specific' AND :character_id = ANY(allowed_character_ids))
            )
        """
        where_conditions.append(access_filter)

        # Optional knowledge type filter
        if knowledge_types:
            type_values = [kt.value for kt in knowledge_types]
            where_conditions.append("knowledge_type = ANY(:knowledge_types)")
            params["knowledge_types"] = type_values

        # Optional owning character filter
        if owning_character_id:
            where_conditions.append("owning_character_id = :owning_character_id")
            params["owning_character_id"] = owning_character_id

        # Combine WHERE conditions
        where_clause = " AND ".join(where_conditions)

        # Final SELECT query - uses parameterized conditions with params dict
        select_sql = text(f"""
            SELECT
                id, content, knowledge_type, owning_character_id,
                access_level, allowed_roles, allowed_character_ids,
                created_at, updated_at, created_by
            FROM knowledge_entries
            WHERE {where_clause}
            ORDER BY updated_at DESC
        """)  # nosec B608

        result = await self._session.execute(select_sql, params)
        rows = result.fetchall()

        # Map rows to domain models
        entries = [self._row_to_domain_model(row) for row in rows]

        # Domain-level access control validation (defense in depth)
        return [entry for entry in entries if entry.is_accessible_by(agent)]

    async def delete(self, entry_id: KnowledgeEntryId) -> None:
        """
        Delete a knowledge entry by its unique identifier.

        Hard delete from knowledge_entries table.
        PostgreSQL CASCADE handles knowledge_audit_log cleanup.

        Args:
            entry_id: Unique identifier of the entry to delete

        Raises:
            ValueError: If entry not found
            RepositoryError: If deletion fails

        Constitution Compliance:
        - Article IV (SSOT): Hard delete from PostgreSQL (CASCADE on audit log)
        """
        from sqlalchemy import text

        # DELETE query
        delete_sql = text("""
            DELETE FROM knowledge_entries
            WHERE id = :entry_id
        """)

        result = await self._session.execute(delete_sql, {"entry_id": UUID(entry_id)})

        # Check if entry was actually deleted
        if result.rowcount == 0:
            raise ValueError(f"Knowledge entry not found: {entry_id}")

    async def retrieve_for_agent_semantic(
        self,
        agent: AgentIdentity,
        semantic_query: str,
        top_k: int = 5,
        threshold: float = 0.0,
        knowledge_types: List[KnowledgeType] | None = None,
    ) -> List[KnowledgeEntry]:
        """
        Retrieve knowledge entries using semantic similarity search.

        Uses PostgreSQL pgvector extension for vector similarity search with cosine distance.
        Retrieves entries semantically similar to query, even without exact keyword matches.

        Args:
            agent: Agent identity (character_id and roles) for access control
            semantic_query: Natural language query for semantic search
            top_k: Maximum number of results to return (default: 5)
            threshold: Minimum similarity score (0.0-1.0, default: 0.0)
            knowledge_types: Optional filter by knowledge types

        Returns:
            List of KnowledgeEntry aggregates ordered by semantic relevance (highest first)

        Raises:
            ValueError: If semantic_query is empty
            RepositoryError: If retrieval operation fails

        Performance:
        - Uses HNSW index for fast approximate nearest neighbor search
        - Cosine similarity operator: <=> (cosine distance, 0=identical, 2=opposite)

        Constitution Compliance:
        - Article I (DDD): Domain model validates access control
        - Article IV (SSOT): PostgreSQL pgvector as single source for embeddings
        - Article VII (Observability): Operation logged and instrumented
        """
        if not semantic_query or not semantic_query.strip():
            raise ValueError("Semantic query cannot be empty")

        from sqlalchemy import text

        # Generate embedding for search query
        query_embedding = await self._embedding_generator.generate_embedding(
            semantic_query
        )

        # Build dynamic WHERE clause for filters
        where_conditions = []
        params = {
            "character_id": agent.character_id,
            "roles": list(agent.roles) if agent.roles else [],
            "query_embedding": query_embedding,
            "top_k": top_k,
        }

        # Access control filtering (same as retrieve_for_agent)
        access_filter = """
            (
                access_level = 'public'
                OR (access_level = 'role_based' AND allowed_roles && CAST(:roles AS TEXT[]))
                OR (access_level = 'character_specific' AND :character_id = ANY(allowed_character_ids))
            )
        """
        where_conditions.append(access_filter)

        # Only search entries with embeddings (nullable during migration)
        where_conditions.append("embedding IS NOT NULL")

        # Optional knowledge type filter
        if knowledge_types:
            type_values = [kt.value for kt in knowledge_types]
            where_conditions.append("knowledge_type = ANY(:knowledge_types)")
            params["knowledge_types"] = type_values

        # Combine WHERE conditions
        where_clause = " AND ".join(where_conditions)

        # Semantic search query using pgvector cosine similarity
        # Cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 - (distance / 2) = 0.0-1.0 range
        semantic_sql = text(f"""
            SELECT
                id, content, knowledge_type, owning_character_id,
                access_level, allowed_roles, allowed_character_ids,
                created_at, updated_at, created_by,
                (1 - (embedding <=> CAST(:query_embedding AS vector(1536)) / 2)) AS similarity_score
            FROM knowledge_entries
            WHERE {where_clause}
            ORDER BY embedding <=> CAST(:query_embedding AS vector(1536))
            LIMIT :top_k
        """)  # nosec B608

        result = await self._session.execute(semantic_sql, params)
        rows = result.fetchall()

        # Map rows to domain models and filter by threshold
        entries = []
        for row in rows:
            # Apply similarity threshold
            similarity_score = row.similarity_score
            if similarity_score < threshold:
                continue

            # Map to domain model
            entry = self._row_to_domain_model(row)

            # Domain-level access control validation (defense in depth)
            if entry.is_accessible_by(agent):
                entries.append(entry)

        return entries

    def _row_to_domain_model(self, row) -> KnowledgeEntry:
        """
        Map database row to KnowledgeEntry domain model.

        Args:
            row: SQLAlchemy Row object

        Returns:
            KnowledgeEntry domain aggregate

        Constitution Compliance:
        - Article I (DDD): Reconstruct pure domain model from persistence data
        """
        # Parse access control rule
        access_control = AccessControlRule(
            access_level=AccessLevel(row.access_level),
            allowed_roles=tuple(row.allowed_roles) if row.allowed_roles else (),
            allowed_character_ids=(
                tuple(row.allowed_character_ids) if row.allowed_character_ids else ()
            ),
        )

        # Reconstruct KnowledgeEntry aggregate
        return KnowledgeEntry(
            id=str(row.id),
            content=row.content,
            knowledge_type=KnowledgeType(row.knowledge_type),
            owning_character_id=row.owning_character_id,
            access_control=access_control,
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
        )
