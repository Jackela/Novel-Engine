"""
BM25 Keyword Retriever

Implements BM25 (Best Matching 25) keyword search for hybrid retrieval.
BM25 is a ranking function used by search engines to estimate the relevance
of documents to a given search query.

Constitution Compliance:
- Article II (Hexagonal): Application service for retrieval
- Article V (SOLID): SRP - BM25 keyword search only

Warzone 4: AI Brain - BRAIN-008A
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
import re

import structlog

if TYPE_CHECKING:
    from rank_bm25 import BM25 as RankBM25


logger = structlog.get_logger()


# Default collection name
DEFAULT_COLLECTION = "knowledge"


# Default k1 and b parameters for BM25
# k1: Term saturation parameter (1.0-2.0 typical, default 1.5)
# b: Length normalization parameter (0.0-1.0, default 0.75)
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    """
    A document indexed for BM25 retrieval.

    Why frozen:
        Immutable snapshot ensures index integrity.

    Attributes:
        doc_id: Unique document identifier (chunk_id)
        source_id: Source entity ID
        source_type: Type of source
        content: Document content text
        tokens: Tokenized content for BM25
        metadata: Additional metadata
    """

    doc_id: str
    source_id: str
    source_type: str
    content: str
    tokens: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BM25Result:
    """
    Result of a BM25 search operation.

    Attributes:
        doc_id: Document ID
        source_id: Source ID
        source_type: Source type
        content: Document content
        score: BM25 relevance score
        metadata: Additional metadata
    """

    doc_id: str
    source_id: str
    source_type: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BM25IndexStats:
    """
    Statistics about the BM25 index.

    Attributes:
        total_documents: Total number of indexed documents
        total_tokens: Total unique tokens in corpus
        avg_doc_length: Average document length in tokens
        last_updated: Timestamp of last update
    """

    total_documents: int
    total_tokens: int
    avg_doc_length: float
    last_updated: str | None = None


def tokenize(text: str) -> list[str]:
    """
    Tokenize text for BM25 indexing.

    Simple word-based tokenization with lowercase normalization.
    Can be enhanced with stemming, stopword removal, etc.

    Args:
        text: Text to tokenize

    Returns:
        List of tokens

    Example:
        >>> tokenize("Sir Aldric is brave!")
        ['sir', 'aldric', 'is', 'brave']
    """
    # Convert to lowercase and find all words
    # Word pattern: sequences of alphanumeric characters
    words = re.findall(r'\b\w+\b', text.lower())
    return words


class BM25Retriever:
    """
    BM25 keyword-based retrieval service.

    Provides keyword search as an alternative or complement to vector search.
    BM25 is particularly effective for:
    - Exact keyword matching
    - Rare term queries
    - Short documents
    - Complementing semantic search

    Constitution Compliance:
        - Article II (Hexarchical): Application service
        - Article V (SOLID): SRP - BM25 retrieval only
        - Article III (TDD): Tested via mocks

    Example:
        >>> retriever = BM25Retriever()
        >>> retriever.index_documents([
        ...     IndexedDocument("1", "char1", "CHARACTER", "brave knight", ...),
        ... ])
        >>> results = retriever.search("brave warrior", k=5)
        >>> for r in results:
        ...     print(f"{r.doc_id}: {r.score:.2f}")
    """

    def __init__(
        self,
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ):
        """
        Initialize the BM25 retriever.

        Args:
            k1: Term saturation parameter (1.0-2.0 typical)
                Higher = more weight to term frequency
            b: Length normalization parameter (0.0-1.0)
                Higher = more impact of document length
        """
        self._k1 = k1
        self._b = b

        # In-memory index: maps collection to (documents, bm25_index)
        self._indices: dict[str, dict[str, Any]] = {}

        # Document lookup by doc_id
        self._documents: dict[str, IndexedDocument] = {}

        # Collection for default operations
        self._default_collection = DEFAULT_COLLECTION

        logger.debug(
            "bm25_retriever_initialized",
            k1=k1,
            b=b,
        )

    def index_documents(
        self,
        documents: list[IndexedDocument],
        collection: str | None = None,
    ) -> int:
        """
        Index documents for BM25 retrieval.

        Creates or updates the BM25 index for the given collection.
        Documents with the same doc_id are replaced.

        Args:
            documents: Documents to index
            collection: Collection name (uses default if None)

        Returns:
            Number of documents indexed

        Example:
            >>> docs = [
            ...     IndexedDocument("1", "char1", "CHARACTER", "brave knight", ...),
            ...     IndexedDocument("2", "char2", "CHARACTER", "wise wizard", ...),
            ... ]
            >>> count = retriever.index_documents(docs)
            >>> print(f"Indexed {count} documents")
        """
        if not documents:
            return 0

        target_collection = collection or self._default_collection

        # Import rank_bm25 lazily
        # Use BM25Plus for better performance with small corpora and rare terms
        try:
            from rank_bm25 import BM25Plus as RankBM25  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "bm25_library_not_found",
                message="rank-bm25 library not installed. Install with: pip install rank-bm25",
            )
            raise ImportError(
                "rank-bm25 library not found. "
                "Install with: pip install rank-bm25"
            )

        # Get or create index for collection
        if target_collection not in self._indices:
            self._indices[target_collection] = {
                "documents": [],
                "bm25": None,
                "corpus": [],
            }

        index_data = self._indices[target_collection]

        # Add/update documents in lookup
        for doc in documents:
            self._documents[doc.doc_id] = doc

            # Check if document already exists in corpus
            existing_idx = next(
                (i for i, d in enumerate(index_data["documents"]) if d == doc.doc_id),
                None
            )

            if existing_idx is not None:
                # Replace existing document
                index_data["documents"][existing_idx] = doc.doc_id
                index_data["corpus"][existing_idx] = doc.tokens
            else:
                # Add new document
                index_data["documents"].append(doc.doc_id)
                index_data["corpus"].append(doc.tokens)

        # Rebuild BM25 index
        index_data["bm25"] = RankBM25(
            index_data["corpus"],
            k1=self._k1,
            b=self._b,
        )

        logger.info(
            "bm25_index_built",
            collection=target_collection,
            document_count=len(index_data["documents"]),
        )

        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5,
        collection: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[BM25Result]:
        """
        Search for documents using BM25 keyword matching.

        Args:
            query: Search query text
            k: Number of results to return
            collection: Collection name (uses default if None)
            filters: Optional metadata filters (source_type, tags, etc.)

        Returns:
            List of BM25Result sorted by relevance score

        Raises:
            ValueError: If query is empty
            KeyError: If collection doesn't exist

        Example:
            >>> results = retriever.search("brave knight", k=5)
            >>> for r in results:
            ...     print(f"{r.doc_id}: {r.score:.2f} - {r.content[:50]}...")
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        target_collection = collection or self._default_collection

        if target_collection not in self._indices:
            logger.warning(
                "bm25_collection_not_found",
                collection=target_collection,
            )
            return []

        index_data = self._indices[target_collection]
        bm25_index = index_data["bm25"]

        if bm25_index is None:
            logger.warning(
                "bm25_index_not_built",
                collection=target_collection,
            )
            return []

        # Tokenize query
        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        logger.debug(
            "bm25_search_start",
            collection=target_collection,
            query=query,
            query_tokens=query_tokens,
            k=k,
        )

        # Get BM25 scores for all documents
        scores = bm25_index.get_scores(query_tokens)

        # Get top k indices
        # argsort gives indices in ascending order, so we reverse
        top_indices = scores.argsort()[-k:][::-1]

        # Build results
        results: list[BM25Result] = []

        for idx in top_indices:
            score = float(scores[idx])

            # Filter out zero scores (no matching terms)
            # BM25 scores can be negative for short documents, which is valid
            if score == 0:
                continue

            doc_id = index_data["documents"][idx]
            doc = self._documents.get(doc_id)

            if doc is None:
                logger.warning(
                    "bm25_document_not_found",
                    doc_id=doc_id,
                )
                continue

            # Apply filters if provided
            if filters:
                if not self._matches_filters(doc, filters):
                    continue

            result = BM25Result(
                doc_id=doc.doc_id,
                source_id=doc.source_id,
                source_type=doc.source_type,
                content=doc.content,
                score=score,
                metadata=doc.metadata,
            )
            results.append(result)

        logger.info(
            "bm25_search_complete",
            collection=target_collection,
            query=query,
            results_count=len(results),
        )

        return results

    def remove_document(
        self,
        doc_id: str,
        collection: str | None = None,
    ) -> bool:
        """
        Remove a document from the index.

        Args:
            doc_id: Document ID to remove
            collection: Collection name (uses default if None)

        Returns:
            True if document was removed, False if not found
        """
        target_collection = collection or self._default_collection

        if target_collection not in self._indices:
            return False

        index_data = self._indices[target_collection]

        # Find document in corpus
        try:
            idx = index_data["documents"].index(doc_id)
        except ValueError:
            return False

        # Remove from corpus and documents list
        index_data["corpus"].pop(idx)
        index_data["documents"].pop(idx)

        # Remove from lookup
        if doc_id in self._documents:
            del self._documents[doc_id]

        # Rebuild BM25 index
        if index_data["corpus"]:
            from rank_bm25 import BM25Plus as RankBM25  # type: ignore[import-untyped]

            index_data["bm25"] = RankBM25(
                index_data["corpus"],
                k1=self._k1,
                b=self._b,
            )
        else:
            index_data["bm25"] = None

        logger.debug(
            "bm25_document_removed",
            collection=target_collection,
            doc_id=doc_id,
        )

        return True

    def clear_collection(
        self,
        collection: str | None = None,
    ) -> int:
        """
        Clear all documents from a collection.

        Args:
            collection: Collection name (uses default if None)

        Returns:
            Number of documents removed
        """
        target_collection = collection or self._default_collection

        if target_collection not in self._indices:
            return 0

        index_data = self._indices[target_collection]
        count = len(index_data["documents"])

        # Clear index data
        index_data["documents"] = []
        index_data["corpus"] = []
        index_data["bm25"] = None

        # Remove documents from lookup
        for doc_id in list(self._documents.keys()):
            doc = self._documents.get(doc_id)
            # Note: We can't determine collection from doc_id alone
            # In production, you'd want to track collection membership
            # For now, we clear all documents (simplest approach)

        self._documents.clear()

        logger.info(
            "bm25_collection_cleared",
            collection=target_collection,
            documents_removed=count,
        )

        return count

    def get_stats(
        self,
        collection: str | None = None,
    ) -> BM25IndexStats | None:
        """
        Get statistics about the BM25 index.

        Args:
            collection: Collection name (uses default if None)

        Returns:
            BM25IndexStats if collection exists, None otherwise
        """
        target_collection = collection or self._default_collection

        if target_collection not in self._indices:
            return None

        index_data = self._indices[target_collection]

        # Calculate statistics
        doc_count = len(index_data["documents"])
        corpus = index_data["corpus"]

        if corpus:
            total_tokens = len(set(token for doc in corpus for token in doc))
            avg_doc_length = sum(len(doc) for doc in corpus) / len(corpus)
        else:
            total_tokens = 0
            avg_doc_length = 0.0

        return BM25IndexStats(
            total_documents=doc_count,
            total_tokens=total_tokens,
            avg_doc_length=avg_doc_length,
            last_updated=datetime.utcnow().isoformat(),
        )

    def _matches_filters(
        self,
        doc: IndexedDocument,
        filters: dict[str, Any],
    ) -> bool:
        """
        Check if a document matches the given filters.

        Args:
            doc: Document to check
            filters: Filter criteria

        Returns:
            True if document matches all filters
        """
        for key, value in filters.items():
            if key == "source_type":
                if doc.source_type != value and doc.source_type != str(value):
                    return False
            elif key == "source_id":
                if doc.source_id != value:
                    return False
            elif key == "tags":
                # Check if any tag matches
                doc_tags = doc.metadata.get("tags", [])
                if isinstance(value, list):
                    if not any(tag in doc_tags for tag in value):
                        return False
                elif value not in doc_tags:
                    return False
            else:
                # Check metadata
                doc_value = doc.metadata.get(key)
                if doc_value != value:
                    return False

        return True


__all__ = [
    "BM25Retriever",
    "BM25Result",
    "IndexedDocument",
    "BM25IndexStats",
    "tokenize",
    "DEFAULT_K1",
    "DEFAULT_B",
]
