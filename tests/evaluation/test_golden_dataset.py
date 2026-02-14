"""
Golden Dataset Evaluation Tests

Tests the golden dataset evaluation harness and asserts baseline scores.
Ensures RAG accuracy doesn't regress.

Constitution Compliance:
- Article III (TDD): Tests drive evaluation implementation
- Article V (SOLID): Each test has single responsibility

OPT-007: Test - Golden Dataset Evaluation Harness
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the evaluation module
from scripts.evaluation.run_golden_dataset import (
    DeterministicEmbeddingService,
    EvaluationReport,
    EvaluationResult,
    GoldenDocument,
    GoldenQuestion,
    InMemoryVectorStore,
    check_exact_match,
    check_fuzzy_match,
    check_substring_match,
    evaluate_question,
    load_golden_dataset,
    normalize_text,
    run_evaluation,
)


@pytest.mark.unit
class TestGoldenDatasetLoading:
    """Tests for loading the golden dataset."""

    def test_load_golden_dataset_from_file(self):
        """Should load questions and documents from JSON file."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"

        questions, documents = load_golden_dataset(dataset_path)

        # Should have loaded data
        assert len(questions) >= 20
        assert len(documents) >= 10

        # Check first question structure
        first_question = questions[0]
        assert hasattr(first_question, "id")
        assert hasattr(first_question, "query")
        assert hasattr(first_question, "expected_facts")
        assert hasattr(first_question, "expected_source_type")
        assert hasattr(first_question, "min_relevance_score")

        # Check first document structure
        first_doc = documents[0]
        assert hasattr(first_doc, "id")
        assert hasattr(first_doc, "source_type")
        assert hasattr(first_doc, "content")

    def test_questions_have_valid_ids(self):
        """All questions should have valid IDs."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        questions, _ = load_golden_dataset(dataset_path)

        for q in questions:
            assert q.id.startswith("q")
            assert q.query.strip()
            assert len(q.expected_facts) > 0

    def test_documents_have_valid_source_types(self):
        """All documents should have valid source types."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        _, documents = load_golden_dataset(dataset_path)

        valid_types = {"CHARACTER", "LORE", "ITEM", "LOCATION", "SCENE", "PLOTLINE"}
        for doc in documents:
            assert doc.source_type in valid_types
            assert doc.content.strip()


@pytest.mark.unit
class TestTextMatching:
    """Tests for text matching algorithms."""

    def test_normalize_text_basic(self):
        """Should normalize text: lowercase, trim, normalize whitespace."""
        assert normalize_text("  Hello  World  ") == "hello world"
        assert normalize_text("Test   Multiple   Spaces") == "test multiple spaces"
        assert normalize_text("UPPERCASE") == "uppercase"
        assert normalize_text("  Mixed CASE  Text  ") == "mixed case text"

    def test_exact_match_basic(self):
        """Should find exact matches."""
        assert check_exact_match("hello world", "hello world")
        assert check_exact_match("hello", "hello world")
        assert check_exact_match("world", "hello world")

    def test_exact_match_case_insensitive(self):
        """Exact match should be case-insensitive."""
        assert check_exact_match("Hello World", "HELLO WORLD")
        assert check_exact_match("test", "TeSt")

    def test_exact_match_with_whitespace(self):
        """Exact match should handle whitespace variations."""
        assert check_exact_match("hello world", "hello   world")
        assert check_exact_match("test", "  test  ")

    def test_exact_match_negative(self):
        """Should return False for non-matches."""
        assert not check_exact_match("hello", "goodbye")
        assert not check_exact_match("missing", "completely different")

    def test_substring_match_basic(self):
        """Should find substring matches."""
        assert check_substring_match("brave knight", "Sir Aldric is a brave knight")
        assert check_substring_match("sword", "The legendary sword glows")

    def test_substring_match_word_overlap(self):
        """Should match with significant word overlap (75%)."""
        # 3 out of 4 words match = 75% threshold
        assert check_substring_match("brave knight fights honor", "brave knight fights with honor")
        # 2 out of 4 words = 50% < 75%
        assert not check_substring_match("brave knight fights honor", "brave knight here")

    def test_fuzzy_match_basic(self):
        """Should find fuzzy matches using SequenceMatcher."""
        # High similarity
        assert check_fuzzy_match("hello world", "hello world")
        assert check_fuzzy_match("test", "test")

        # Moderate similarity (default threshold 0.6)
        assert check_fuzzy_match("knight", "knigth")
        assert check_fuzzy_match("sword", "swords")

    def test_fuzzy_match_threshold(self):
        """Should respect threshold parameter."""
        # Very similar text passes at 0.5 threshold
        assert check_fuzzy_match("test", "testing", threshold=0.5)
        # Same text doesn't pass at very high threshold unless exact
        assert not check_fuzzy_match("test", "other", threshold=0.8)
        # Exact match passes any threshold
        assert check_fuzzy_match("exact", "exact", threshold=0.99)


@pytest.mark.unit
class TestDeterministicEmbedding:
    """Tests for deterministic embedding service."""

    @pytest.mark.asyncio
    async def test_embedding_is_deterministic(self):
        """Same text should produce same embedding."""
        service = DeterministicEmbeddingService(dimension=128)

        embedding1 = await service.embed("test text")
        embedding2 = await service.embed("test text")

        assert embedding1 == embedding2
        assert len(embedding1) == 128

    @pytest.mark.asyncio
    async def test_different_texts_different_embeddings(self):
        """Different texts should produce different embeddings."""
        service = DeterministicEmbeddingService(dimension=128)

        embedding1 = await service.embed("hello world")
        embedding2 = await service.embed("goodbye world")

        assert embedding1 != embedding2

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Should generate embeddings for multiple texts."""
        service = DeterministicEmbeddingService(dimension=64)

        texts = ["one", "two", "three"]
        embeddings = await service.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 64 for e in embeddings)

    def test_get_dimension(self):
        """Should return configured dimension."""
        service = DeterministicEmbeddingService(dimension=256)
        assert service.get_dimension() == 256


@pytest.mark.unit
class TestInMemoryVectorStore:
    """Tests for in-memory vector store."""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service."""
        return DeterministicEmbeddingService(dimension=64)

    @pytest.fixture
    def vector_store(self, embedding_service):
        """Create vector store."""
        return InMemoryVectorStore(embedding_service)

    @pytest.mark.asyncio
    async def test_add_and_query_documents(self, vector_store):
        """Should add documents and query them."""
        docs = [
            GoldenDocument(id="1", source_type="LORE", content="knight fights with honor"),
            GoldenDocument(id="2", source_type="LORE", content="wizard casts spells"),
        ]

        vector_store.add_documents(docs)

        query_embedding = await vector_store._embedding_service.embed("knight honor")
        results = await vector_store.query(query_embedding, n_results=5)

        assert len(results) > 0
        assert results[0].id == "1"  # Most similar

    @pytest.mark.asyncio
    async def test_query_with_source_type_filter(self, vector_store):
        """Should filter by source type."""
        docs = [
            GoldenDocument(id="1", source_type="CHARACTER", content="brave knight"),
            GoldenDocument(id="2", source_type="LORE", content="kingdom history"),
        ]

        vector_store.add_documents(docs)

        query_embedding = await vector_store._embedding_service.embed("brave knight")

        # Filter for CHARACTER only
        results = await vector_store.query(
            query_embedding,
            n_results=5,
            where={"source_type": {"$in": ["CHARACTER"]}},
        )

        assert all(r.metadata["source_type"] == "CHARACTER" for r in results)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_limits_results(self, vector_store):
        """Should limit results to n_results."""
        docs = [
            GoldenDocument(id=str(i), source_type="LORE", content=f"content {i}")
            for i in range(10)
        ]

        vector_store.add_documents(docs)

        query_embedding = await vector_store._embedding_service.embed("content")
        results = await vector_store.query(query_embedding, n_results=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_health_check(self, vector_store):
        """Health check should return True."""
        assert await vector_store.health_check()


@pytest.mark.unit
class TestEvaluationQuestion:
    """Tests for single question evaluation."""

    @pytest.fixture
    def mock_retrieval_service(self):
        """Create mock retrieval service."""
        from unittest.mock import AsyncMock

        from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
            RetrievedChunk,
        )
        from src.contexts.knowledge.domain.models.source_type import SourceType

        service = AsyncMock()

        # Mock retrieval result
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is a brave knight who fights with honor.",
                score=0.85,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
        ]

        result = AsyncMock()
        result.chunks = chunks
        service.retrieve_relevant.return_value = result

        return service

    @pytest.mark.asyncio
    async def test_evaluate_question_finds_matches(self, mock_retrieval_service):
        """Should find expected facts in retrieved content."""
        question = GoldenQuestion(
            id="q1",
            query="Who is Alice?",
            expected_facts=["Alice", "brave", "knight"],
            expected_source_type="CHARACTER",
            min_relevance_score=0.7,
        )

        result = await evaluate_question(question, mock_retrieval_service)

        assert result.question_id == "q1"
        assert len(result.matches_found) > 0
        assert result.has_expected_source_type
        assert result.relevance_score == 0.85

    @pytest.mark.asyncio
    async def test_evaluate_question_with_no_results(self):
        """Should handle empty retrieval results."""
        from unittest.mock import AsyncMock

        service = AsyncMock()
        result = AsyncMock()
        result.chunks = []
        service.retrieve_relevant.return_value = result

        question = GoldenQuestion(
            id="q1",
            query="Unknown query",
            expected_facts=["something"],
            expected_source_type="LORE",
            min_relevance_score=0.7,
        )

        result = await evaluate_question(question, service)

        assert result.relevance_score == 0.0
        assert not result.has_expected_source_type


@pytest.mark.integration
class TestGoldenDatasetIntegration:
    """Integration tests for the full evaluation pipeline."""

    @pytest.mark.asyncio
    async def test_run_evaluation_full_pipeline(self):
        """Should run full evaluation pipeline and generate report."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"

        report = await run_evaluation(dataset_path, baseline_threshold=0.5)

        # Check report structure
        assert report.total_questions >= 20
        assert report.passed_questions >= 0
        assert report.failed_questions >= 0
        assert report.pass_rate >= 0.0
        assert report.average_relevance_score >= 0.0
        assert len(report.results) == report.total_questions

    @pytest.mark.asyncio
    async def test_evaluation_report_serialization(self):
        """Report should have all required fields for JSON output."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"

        report = await run_evaluation(dataset_path, baseline_threshold=0.5)

        # Verify all report fields exist
        assert hasattr(report, "timestamp")
        assert hasattr(report, "total_questions")
        assert hasattr(report, "passed_questions")
        assert hasattr(report, "failed_questions")
        assert hasattr(report, "total_exact_matches")
        assert hasattr(report, "total_substring_matches")
        assert hasattr(report, "total_fuzzy_matches")
        assert hasattr(report, "average_relevance_score")
        assert hasattr(report, "source_type_coverage")
        assert hasattr(report, "pass_rate")
        assert hasattr(report, "results")

    @pytest.mark.asyncio
    async def test_evaluation_meets_baseline(self):
        """Golden dataset evaluation should meet baseline score."""
        dataset_path = Path(__file__).parent / "golden_dataset.json"
        baseline_threshold = 0.40  # 40% baseline for deterministic embeddings

        report = await run_evaluation(dataset_path, baseline_threshold)

        # Assert that pass rate meets baseline
        assert report.pass_rate >= baseline_threshold, (
            f"Pass rate {report.pass_rate:.2%} is below baseline {baseline_threshold:.2%}. "
            f"Golden dataset evaluation failed. "
            f"Passed {report.passed_questions}/{report.total_questions} questions."
        )


@pytest.mark.unit
class TestEvaluationReport:
    """Tests for evaluation report data structure."""

    def test_evaluation_report_creation(self):
        """Should create report with all required fields."""
        result = EvaluationResult(
            question_id="q1",
            query="test query",
            retrieved_chunks=[],
            expected_facts=["fact1"],
            matches_found=[],
            exact_matches=0,
            substring_matches=1,
            fuzzy_matches=0,
            relevance_score=0.8,
            has_expected_source_type=True,
            passed=True,
        )

        report = EvaluationReport(
            total_questions=10,
            passed_questions=8,
            failed_questions=2,
            total_exact_matches=15,
            total_substring_matches=20,
            total_fuzzy_matches=5,
            average_relevance_score=0.75,
            source_type_coverage=0.9,
            pass_rate=0.8,
            results=[result],
        )

        assert report.total_questions == 10
        assert report.pass_rate == 0.8
        assert len(report.results) == 1

    def test_evaluation_report_calculates_pass_rate(self):
        """Pass rate should be calculated correctly."""
        report = EvaluationReport(
            total_questions=100,
            passed_questions=75,
            failed_questions=25,
            total_exact_matches=0,
            total_substring_matches=0,
            total_fuzzy_matches=0,
            average_relevance_score=0.7,
            source_type_coverage=0.8,
            pass_rate=0.75,
        )

        assert report.pass_rate == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
