#!/usr/bin/env python3
"""
Semantic Memory System
======================

This module implements a semantic memory system that preserves factual
knowledge, concepts, and learned information in organized taxonomies. Each
fact is stored with associated metadata like confidence and source.
"""

import asyncio
import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from src.core.data_models import (
    ErrorInfo,
    MemoryItem,
    MemoryType,
    StandardResponse,
)
from src.core.types import AgentID
from src.database.context_db import ContextDatabase

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeFact:
    """
    Represents a structured piece of factual information, including confidence
    levels and source attribution.
    """

    fact_id: str
    subject: str
    predicate: str
    object_value: str
    confidence: float = 1.0
    source_memory_id: str = ""
    learned_at: datetime = field(default_factory=datetime.now)
    last_confirmed: datetime = field(default_factory=datetime.now)
    confirmation_count: int = 1

    def __post_init__(self):
        """Validates data and generates a fact ID if not provided."""
        self.confidence = max(0.0, min(1.0, self.confidence))
        if not self.fact_id:
            fact_hash = hashlib.sha1(
                f"{self.subject}{self.predicate}{self.object_value}".encode()
            ).hexdigest()[:8]
            self.fact_id = f"fact_{fact_hash}"

    def confirm_fact(self, source_memory_id: str = ""):
        """Increases confirmation count and confidence in the fact."""
        self.confirmation_count += 1
        self.last_confirmed = datetime.now()
        confidence_boost = 0.1 / self.confirmation_count
        self.confidence = min(1.0, self.confidence + confidence_boost)
        if source_memory_id and source_memory_id != self.source_memory_id:
            self.confidence = min(1.0, self.confidence + 0.05)

    def to_natural_language(self) -> str:
        """Returns a natural language representation of the fact."""
        return f"{self.subject} {self.predicate} {self.object_value}"


@dataclass
class ConceptNode:
    """
    Represents a node in a hierarchical concept graph, organizing knowledge
    into taxonomies and semantic networks.
    """

    concept_id: str
    concept_name: str
    parent_concepts: Set[str] = field(default_factory=set)
    child_concepts: Set[str] = field(default_factory=set)
    associated_facts: Set[str] = field(default_factory=set)
    importance_score: float = 0.0


class SemanticMemory:
    """
    Manages the storage and retrieval of factual knowledge in a structured
    manner, using a system of facts and concept nodes.
    """

    def __init__(
        self,
        agent_id: AgentID,
        database: ContextDatabase,
        max_facts: int = 5000,
        confidence_threshold: float = 0.3,
    ):
        """
        Initializes the SemanticMemory system.

        Args:
            agent_id: The ID of the agent this memory belongs to.
            database: The database connection for persistence.
            max_facts: Maximum number of facts to store before pruning.
            confidence_threshold: Minimum confidence for retaining a fact.
        """
        self.agent_id = agent_id
        self.database = database
        self.max_facts = max_facts
        self.confidence_threshold = confidence_threshold

        self._facts: Dict[str, KnowledgeFact] = {}
        self._concepts: Dict[str, ConceptNode] = {}

        self._subject_index: Dict[str, List[str]] = defaultdict(list)
        self._predicate_index: Dict[str, List[str]] = defaultdict(list)

        self.total_facts_learned = 0
        self.total_concepts_formed = 0

        self._fact_patterns = [
            (r"(\w+(?:\s+\w+)*) is (?:a |an )?(.+)", "is"),
            (r"(\w+(?:\s+\w+)*) has (.+)", "has"),
            (r"(\w+(?:\s+\w+)*) can (.+)", "can"),
        ]

        logger.info(f"SemanticMemory initialized for {agent_id}")

    async def extract_and_store_knowledge(
        self, memory: MemoryItem
    ) -> StandardResponse:
        """
        Extracts factual knowledge from memory content and stores it as
        structured facts, creating concepts and links automatically.
        """
        try:
            extracted_facts = self._extract_facts_from_content(
                memory.content, memory.memory_id, memory.relevance_score
            )

            entities = self._extract_entities(memory.content)
            for entity in entities:
                await self._ensure_concept_exists(entity)

            stored_count = 0
            for fact in extracted_facts:
                storage_result = await self._store_fact(fact)
                if storage_result.success:
                    stored_count += 1
                    await self._associate_fact_with_concepts(fact)

            self.total_facts_learned += stored_count

            if len(self._facts) > self.max_facts:
                await self._prune_knowledge()

            logger.info(
                f"Extracted {stored_count} facts from memory {memory.memory_id}"
            )

            return StandardResponse(
                success=True,
                data={
                    "facts_extracted": stored_count,
                    "entities_found": len(entities),
                },
            )

        except Exception as e:
            logger.error(f"Knowledge extraction failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="KNOWLEDGE_EXTRACTION_FAILED", message=str(e)
                ),
            )

    def _extract_facts_from_content(
        self, content: str, memory_id: str, relevance: float
    ) -> List[KnowledgeFact]:
        """Extracts facts from a string of text using regex patterns."""
        facts = []
        for pattern, predicate in self._fact_patterns:
            for match in re.findall(pattern, content, re.IGNORECASE):
                subject, object_value = match
                facts.append(
                    KnowledgeFact(
                        fact_id="",
                        subject=subject.strip(),
                        predicate=predicate,
                        object_value=object_value.strip(),
                        source_memory_id=memory_id,
                        confidence=relevance * 0.8,
                    )
                )
        return facts

    async def query_facts_by_subject(
        self, subject: str, confidence_threshold: Optional[float] = None
    ) -> StandardResponse:
        """
        Retrieves all facts about a specific subject, filtered by confidence.
        """
        try:
            subject_lower = subject.lower()
            threshold = confidence_threshold or self.confidence_threshold

            fact_ids = self._subject_index.get(subject_lower, [])
            matching_facts = [
                self._facts[fid]
                for fid in fact_ids
                if self._facts[fid].confidence >= threshold
            ]

            matching_facts.sort(key=lambda f: f.confidence, reverse=True)

            fact_statements = [
                fact.to_natural_language() for fact in matching_facts
            ]

            logger.info(
                f"Retrieved {len(matching_facts)} facts about '{subject}'"
            )

            return StandardResponse(
                success=True,
                data={"subject": subject, "facts": fact_statements},
            )

        except Exception as e:
            logger.error(
                f"Fact retrieval by subject failed: {e}", exc_info=True
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="SUBJECT_FACT_RETRIEVAL_FAILED", message=str(e)
                ),
            )

    async def query_facts_by_predicate(
        self, predicate: str, limit: int = 20
    ) -> StandardResponse:
        """
        Retrieves facts matching a specific relationship type.
        """
        try:
            predicate_lower = predicate.lower()
            fact_ids = self._predicate_index.get(predicate_lower, [])
            matching_facts = [
                self._facts[fid]
                for fid in fact_ids
                if self._facts[fid].confidence >= self.confidence_threshold
            ]

            matching_facts.sort(key=lambda f: f.confidence, reverse=True)

            limited_facts = matching_facts[:limit]
            fact_statements = [
                fact.to_natural_language() for fact in limited_facts
            ]

            logger.info(
                f"Retrieved {len(limited_facts)} facts with predicate '{predicate}'"
            )

            return StandardResponse(
                success=True,
                data={"predicate": predicate, "facts": fact_statements},
            )

        except Exception as e:
            logger.error(
                f"Fact retrieval by predicate failed: {e}", exc_info=True
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PREDICATE_FACT_RETRIEVAL_FAILED", message=str(e)
                ),
            )

    async def get_concept_knowledge(
        self, concept_name: str
    ) -> StandardResponse:
        """
        Retrieves comprehensive knowledge about a concept, including its
        relationships and associated facts.
        """
        try:
            concept_lower = concept_name.lower()
            concept = self._concepts.get(concept_lower)

            if not concept:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="CONCEPT_NOT_FOUND",
                        message=f"Concept '{concept_name}' not found",
                    ),
                )

            associated_facts = [
                self._facts[fid].to_natural_language()
                for fid in concept.associated_facts
                if fid in self._facts
            ]

            knowledge = {
                "concept_name": concept.concept_name,
                "importance_score": concept.importance_score,
                "associated_facts": associated_facts,
                "parent_concepts": list(concept.parent_concepts),
                "child_concepts": list(concept.child_concepts),
            }

            logger.info(f"Retrieved knowledge for concept '{concept_name}'")

            return StandardResponse(success=True, data=knowledge)

        except Exception as e:
            logger.error(
                f"Concept knowledge retrieval failed: {e}", exc_info=True
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CONCEPT_KNOWLEDGE_RETRIEVAL_FAILED", message=str(e)
                ),
            )

    async def _store_fact(self, fact: KnowledgeFact) -> StandardResponse:
        """Stores a single fact, or confirms it if it already exists."""
        if fact.fact_id in self._facts:
            self._facts[fact.fact_id].confirm_fact(fact.source_memory_id)
            return StandardResponse(success=True, data={"confirmed": True})

        self._facts[fact.fact_id] = fact
        self._subject_index[fact.subject.lower()].append(fact.fact_id)
        self._predicate_index[fact.predicate.lower()].append(fact.fact_id)
        return StandardResponse(success=True, data={"stored": True})

    async def _ensure_concept_exists(self, entity_name: str) -> ConceptNode:
        """Ensures a concept node exists for a given entity name."""
        entity_lower = entity_name.lower()
        if entity_lower not in self._concepts:
            self._concepts[entity_lower] = ConceptNode(
                concept_id=entity_lower, concept_name=entity_name
            )
            self.total_concepts_formed += 1
        return self._concepts[entity_lower]

    async def _associate_fact_with_concepts(self, fact: KnowledgeFact):
        """Links a fact to its subject and object concepts."""
        subject_concept = await self._ensure_concept_exists(fact.subject)
        subject_concept.associated_facts.add(fact.fact_id)

        if self._is_entity(fact.object_value):
            object_concept = await self._ensure_concept_exists(
                fact.object_value
            )
            object_concept.associated_facts.add(fact.fact_id)

    def _extract_entities(self, content: str) -> List[str]:
        """Extracts named entities from text content."""
        # This is a simple heuristic. A proper NER model would be better.
        return [
            word
            for word in re.findall(r"\b[A-Z][a-z]+\b", content)
            if len(word) > 2
        ]

    def _is_entity(self, text: str) -> bool:
        """Determines if a string is likely to be a named entity."""
        return len(text) > 0 and text[0].isupper()

    async def _prune_knowledge(self):
        """Removes low-confidence facts to manage memory size."""
        if len(self._facts) <= self.max_facts:
            return

        sorted_facts = sorted(self._facts.values(), key=lambda f: f.confidence)

        num_to_prune = len(self._facts) - self.max_facts
        facts_to_prune = sorted_facts[:num_to_prune]

        for fact in facts_to_prune:
            del self._facts[fact.fact_id]
            # This is simplified; a real implementation would clean indices
            # too.

        logger.info(f"Pruned {num_to_prune} low-confidence facts.")

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the semantic memory."""
        if not self._facts:
            return {"total_facts": 0, "average_confidence": 0.0}

        total_confidence = sum(
            fact.confidence for fact in self._facts.values()
        )

        return {
            "total_facts": len(self._facts),
            "total_concepts": len(self._concepts),
            "average_confidence": (
                total_confidence / len(self._facts) if self._facts else 0
            ),
        }


async def test_semantic_memory():
    """Tests the SemanticMemory system."""
    print("Testing Semantic Memory...")

    db = ContextDatabase(":memory:")
    await db.initialize()

    semantic_memory = SemanticMemory("test_agent", db)

    test_memory = MemoryItem(
        agent_id="test_agent",
        memory_type=MemoryType.OBSERVATION,
        content="The sky is blue. The AI can learn.",
        relevance_score=0.9,
    )

    result = await semantic_memory.extract_and_store_knowledge(test_memory)
    print(
        f"Knowledge extraction successful: {result.success}, Facts extracted: {result.data.get('facts_extracted')}"
    )

    facts_result = await semantic_memory.query_facts_by_subject("sky")
    print(
        f"Query for 'sky' facts successful: {facts_result.success}, Facts: {facts_result.data.get('facts')}"
    )
    assert "sky is blue" in facts_result.data.get("facts", [])

    concept_result = await semantic_memory.get_concept_knowledge("sky")
    print(f"Query for 'sky' concept successful: {concept_result.success}")
    assert "sky is blue" in concept_result.data.get("associated_facts", [])

    stats = semantic_memory.get_memory_statistics()
    print(f"Semantic Memory Stats: {stats}")

    await db.close()
    print("Semantic Memory testing complete.")


if __name__ == "__main__":
    asyncio.run(test_semantic_memory())
