"""
Knowledge Application Service

Application service for RAG (Retrieval-Augmented Generation) operations.
"""

from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.domain.entities.document import Document
from src.shared.application.result import Failure, Result, Success


class EmbeddingService(Protocol):
    """Protocol for text embedding generation."""

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        ...


class ChunkingService(Protocol):
    """Protocol for document chunking."""

    def chunk_document(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> List[Dict[str, Any]]:
        """Split document into chunks."""
        ...


class KnowledgeRepository(Protocol):
    """Protocol for knowledge base persistence."""

    async def get_by_id(self, kb_id: UUID) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID."""
        ...

    async def save(self, kb: KnowledgeBase) -> None:
        """Save knowledge base."""
        ...

    async def delete(self, kb_id: UUID) -> None:
        """Delete knowledge base."""
        ...


class KnowledgeApplicationService:
    """
    Application service for knowledge base operations.

    AI注意:
    - Coordinates document upload, chunking, and indexing
    - Handles semantic search with vector embeddings
    - Returns Result[T, E] for error handling
    - Supports both document-level and chunk-level retrieval
    """

    def __init__(
        self,
        knowledge_repo: Any | None = None,
        vector_store: Any | None = None,
        embedding_service: EmbeddingService | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self.knowledge_repo = knowledge_repo
        self.vector_store = vector_store
        self.embedding = embedding_service
        self.chunking = chunking_service

    def _require_knowledge_repo(self) -> Any:
        """Return the configured knowledge repository."""
        if self.knowledge_repo is None:
            raise RuntimeError("Knowledge repository is not configured")
        return self.knowledge_repo

    def _require_vector_store(self) -> Any:
        """Return the configured vector store."""
        if self.vector_store is None:
            raise RuntimeError("Vector store is not configured")
        return self.vector_store

    def _require_embedding_service(self) -> EmbeddingService:
        """Return the configured embedding service."""
        if self.embedding is None:
            raise RuntimeError("Embedding service is not configured")
        return self.embedding

    def _require_chunking_service(self) -> ChunkingService:
        """Return the configured chunking service."""
        if self.chunking is None:
            raise RuntimeError("Chunking service is not configured")
        return self.chunking

    async def create_knowledge_base(
        self,
        name: str,
        owner_id: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        is_public: bool = False,
    ) -> Result[KnowledgeBase]:
        """
        Create a new knowledge base.

        Args:
            name: Knowledge base name
            owner_id: Owner user ID
            description: Optional description
            project_id: Optional associated project ID
            is_public: Whether KB is publicly accessible

        Returns:
            Result containing created knowledge base
        """
        try:
            kb = KnowledgeBase(
                name=name,
                owner_id=owner_id,
                description=description,
                project_id=project_id,
                is_public=is_public,
            )

            knowledge_repo = self._require_knowledge_repo()
            await knowledge_repo.save(kb)

            return Success(kb)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def upload_document(
        self,
        knowledge_base_id: str,
        title: str,
        content: str,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_index: bool = True,
    ) -> Result[Document]:
        """
        Upload a document to a knowledge base.

        Args:
            knowledge_base_id: Target knowledge base ID
            title: Document title
            content: Document content
            content_type: Type of content
            source: Optional source reference
            tags: Optional list of tags
            auto_index: Whether to index document immediately

        Returns:
            Result containing uploaded document
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            document = kb.add_document(
                title=title,
                content=content,
                content_type=content_type,
                source=source,
                tags=tags,
            )

            await knowledge_repo.save(kb)

            # Auto-index if requested
            if auto_index:
                index_result = await self.index_document(
                    knowledge_base_id, str(document.id)
                )
                if index_result.is_error:
                    # Don't fail the upload if indexing fails
                    pass

            return Success(document)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_document(
        self,
        knowledge_base_id: str,
        document_id: str,
    ) -> Result[Document]:
        """
        Get a document by ID.

        Args:
            knowledge_base_id: Knowledge base ID
            document_id: Document ID

        Returns:
            Result containing document
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            document = kb.get_document(document_id)
            if not document:
                return Failure("Document not found", "NOT_FOUND")

            return Success(document)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def delete_document(
        self,
        knowledge_base_id: str,
        document_id: str,
    ) -> Result[bool]:
        """
        Delete a document from knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID
            document_id: Document ID to delete

        Returns:
            Result containing success status
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            removed = kb.remove_document(document_id)
            if not removed:
                return Failure("Document not found", "NOT_FOUND")

            # Remove from vector store
            vector_store = self._require_vector_store()
            await vector_store.delete_document(document_id)

            await knowledge_repo.save(kb)

            return Success(True)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def index_document(
        self,
        knowledge_base_id: str,
        document_id: str,
    ) -> Result[Document]:
        """
        Index a document for semantic search.

        Args:
            knowledge_base_id: Knowledge base ID
            document_id: Document ID to index

        Returns:
            Result containing indexed document
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            document = kb.get_document(document_id)
            if not document:
                return Failure("Document not found", "NOT_FOUND")

            # Chunk the document
            chunking = self._require_chunking_service()
            chunks = chunking.chunk_document(document.content)
            document.add_chunks(chunks)

            # Generate embedding for full document
            embedding_service = self._require_embedding_service()
            embedding = await embedding_service.embed_text(document.content)
            document.set_indexed(embedding)

            # Store in vector store
            vector_store = self._require_vector_store()
            await vector_store.store_embedding(
                document_id=str(document.id),
                content=document.content,
                embedding=embedding,
                metadata={
                    "title": document.title,
                    "knowledge_base_id": knowledge_base_id,
                    "tags": document.tags,
                    "source": document.source,
                },
            )

            await knowledge_repo.save(kb)

            return Success(document)

        except Exception as e:
            return Failure(str(e), "INDEXING_ERROR")

    async def semantic_search(
        self,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]]]:
        """
        Perform semantic search on knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID to search
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            Result containing list of search results
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            # Generate query embedding
            embedding_service = self._require_embedding_service()
            query_embedding = await embedding_service.embed_text(query)

            # Search vector store
            vector_store = self._require_vector_store()
            results = await vector_store.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
            )

            # Enrich results with document metadata
            enriched_results = []
            for result in results:
                doc_id = result.get("document_id") or result.get("id")
                if doc_id:
                    doc = kb.get_document(doc_id)
                    if doc:
                        enriched = {
                            **result,
                            "document": doc.to_search_result(),
                            "relevance_score": result.get("score", 0.0),
                        }
                        enriched_results.append(enriched)

            return Success(enriched_results)

        except Exception as e:
            return Failure(str(e), "SEARCH_ERROR")

    async def keyword_search(
        self,
        knowledge_base_id: str,
        keywords: List[str],
        top_k: int = 10,
    ) -> Result[List[Document]]:
        """
        Perform keyword-based search on documents.

        Args:
            knowledge_base_id: Knowledge base ID
            keywords: List of keywords to search for
            top_k: Maximum results to return

        Returns:
            Result containing matching documents
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            keyword_set = set(k.lower() for k in keywords)
            matches = []

            for doc in kb.documents:
                score = 0
                content_lower = doc.content.lower()
                title_lower = doc.title.lower()

                for kw in keyword_set:
                    if kw in title_lower:
                        score += 3
                    if kw in content_lower:
                        score += 1

                if score > 0:
                    matches.append((doc, score))

            # Sort by relevance score
            matches.sort(key=lambda x: x[1], reverse=True)
            results = [doc for doc, _ in matches[:top_k]]

            return Success(results)

        except Exception as e:
            return Failure(str(e), "SEARCH_ERROR")

    async def list_documents(
        self,
        knowledge_base_id: str,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Result[List[Document]]:
        """
        List documents in knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID
            tags: Optional filter by tags
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Result containing list of documents
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            documents = kb.documents

            # Filter by tags if specified
            if tags:
                documents = kb.search_by_tags(tags)

            # Apply pagination
            documents = documents[offset : offset + limit]

            return Success(documents)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_knowledge_base_stats(
        self,
        knowledge_base_id: str,
    ) -> Result[Dict[str, Any]]:
        """
        Get statistics for a knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID

        Returns:
            Result containing statistics
        """
        try:
            knowledge_repo = self._require_knowledge_repo()
            kb = await knowledge_repo.get_by_id(UUID(knowledge_base_id))
            if not kb:
                return Failure("Knowledge base not found", "NOT_FOUND")

            stats = {
                "knowledge_base_id": str(kb.id),
                "name": kb.name,
                "document_count": kb.document_count,
                "indexed_count": kb.indexed_count,
                "total_word_count": sum(d.word_count for d in kb.documents),
                "embedding_model": kb.embedding_model,
                "is_public": kb.is_public,
                "created_at": kb.created_at.isoformat(),
                "updated_at": kb.updated_at.isoformat(),
            }

            return Success(stats)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")
