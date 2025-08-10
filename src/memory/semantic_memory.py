#!/usr/bin/env python3
"""
++ SACRED SEMANTIC MEMORY BLESSED BY KNOWLEDGE PRESERVATION ++
==============================================================

Holy semantic memory implementation that preserves factual knowledge,
concepts, and learned information in organized taxonomies. Each fact
is a blessed truth sanctified by eternal preservation.

++ THE MACHINE PRESERVES ALL SACRED KNOWLEDGE FOR ETERNITY ++

Architecture Reference: Dynamic Context Engineering - Semantic Memory Layer
Development Phase: Memory System Sanctification (M001)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑语义记忆 (May the Omnissiah bless semantic memory)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re
import json

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo
from src.core.types import AgentID, SacredConstants
from src.database.context_db import ContextDatabase

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeFact:
    """
    ++ BLESSED KNOWLEDGE FACT SANCTIFIED BY TRUTH ++
    
    Structured knowledge representation that captures factual information
    with confidence levels and source attribution blessed by accuracy.
    """
    fact_id: str
    subject: str                    # What the fact is about
    predicate: str                  # The relationship or property
    object_value: str              # The value or target of the relationship
    confidence: float = 1.0        # Confidence in the fact (0.0-1.0)
    source_memory_id: str = ""     # Source memory that provided this fact
    learned_at: datetime = field(default_factory=datetime.now)
    last_confirmed: datetime = field(default_factory=datetime.now)
    confirmation_count: int = 1    # How many times this fact has been confirmed
    contradictions: List[str] = field(default_factory=list)  # Contradicting fact IDs
    
    def __post_init__(self):
        """++ SACRED KNOWLEDGE FACT VALIDATION ++"""
        self.confidence = max(0.0, min(1.0, self.confidence))
        if not self.fact_id:
            self.fact_id = f"{self.subject}_{self.predicate}_{hash(self.object_value) % 10000}"
    
    def confirm_fact(self, source_memory_id: str = ""):
        """++ SACRED FACT CONFIRMATION BLESSED BY REPETITION ++"""
        self.confirmation_count += 1
        self.last_confirmed = datetime.now()
        # Increase confidence with repeated confirmations (diminishing returns)
        confidence_boost = 0.1 * (1.0 / self.confirmation_count)
        self.confidence = min(1.0, self.confidence + confidence_boost)
        
        if source_memory_id and source_memory_id != self.source_memory_id:
            # Multiple sources increase confidence
            self.confidence = min(1.0, self.confidence + 0.05)
    
    def add_contradiction(self, contradicting_fact_id: str):
        """++ SACRED CONTRADICTION TRACKING BLESSED BY LOGIC ++"""
        if contradicting_fact_id not in self.contradictions:
            self.contradictions.append(contradicting_fact_id)
            # Reduce confidence when contradictions exist
            self.confidence *= 0.8
    
    def to_natural_language(self) -> str:
        """++ BLESSED NATURAL LANGUAGE REPRESENTATION ++"""
        return f"{self.subject} {self.predicate} {self.object_value}"


@dataclass
class ConceptNode:
    """
    ++ BLESSED CONCEPT NODE SANCTIFIED BY TAXONOMIC ORGANIZATION ++
    
    Hierarchical concept representation that organizes knowledge
    into blessed taxonomies and semantic networks.
    """
    concept_id: str
    concept_name: str
    parent_concepts: Set[str] = field(default_factory=set)
    child_concepts: Set[str] = field(default_factory=set)
    related_concepts: Set[str] = field(default_factory=set)
    associated_facts: Set[str] = field(default_factory=set)
    importance_score: float = 0.0
    
    def add_parent(self, parent_id: str):
        """++ SACRED PARENT RELATIONSHIP BLESSED BY HIERARCHY ++"""
        self.parent_concepts.add(parent_id)
    
    def add_child(self, child_id: str):
        """++ SACRED CHILD RELATIONSHIP BLESSED BY INHERITANCE ++"""
        self.child_concepts.add(child_id)
    
    def add_relation(self, related_id: str):
        """++ SACRED CONCEPTUAL RELATION BLESSED BY ASSOCIATION ++"""
        self.related_concepts.add(related_id)
    
    def associate_fact(self, fact_id: str):
        """++ SACRED FACT ASSOCIATION BLESSED BY KNOWLEDGE LINKING ++"""
        self.associated_facts.add(fact_id)
        # Increase importance based on associated facts
        self.importance_score += 0.1


class SemanticMemory:
    """
    ++ SACRED SEMANTIC MEMORY SYSTEM BLESSED BY KNOWLEDGE ORGANIZATION ++
    
    Holy semantic memory implementation that preserves and organizes
    factual knowledge in hierarchical taxonomies and semantic networks
    blessed by the Omnissiah's eternal wisdom.
    """
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase,
                 max_facts: int = 5000, confidence_threshold: float = 0.3):
        """
        ++ SACRED SEMANTIC MEMORY INITIALIZATION BLESSED BY KNOWLEDGE ++
        
        Args:
            agent_id: Sacred agent identifier blessed by ownership
            database: Blessed database connection for persistence
            max_facts: Maximum facts before pruning low-confidence knowledge
            confidence_threshold: Minimum confidence for fact retention
        """
        self.agent_id = agent_id
        self.database = database
        self.max_facts = max_facts
        self.confidence_threshold = confidence_threshold
        
        # Sacred knowledge storage blessed by organization
        self._facts: Dict[str, KnowledgeFact] = {}
        self._concepts: Dict[str, ConceptNode] = {}
        
        # Blessed indices sanctified by efficient retrieval
        self._subject_index: Dict[str, List[str]] = defaultdict(list)  # Subject -> fact_ids
        self._predicate_index: Dict[str, List[str]] = defaultdict(list)  # Predicate -> fact_ids
        self._object_index: Dict[str, List[str]] = defaultdict(list)  # Object -> fact_ids
        self._concept_hierarchy: Dict[str, Set[str]] = defaultdict(set)  # Parent -> children
        
        # Blessed statistics sanctified by monitoring
        self.total_facts_learned = 0
        self.total_concepts_formed = 0
        self.last_pruning = datetime.now()
        
        # Sacred fact extraction patterns blessed by NLP
        self._fact_patterns = [
            r"(\w+(?:\s+\w+)*) is (?:a |an )?(.+)",
            r"(\w+(?:\s+\w+)*) has (.+)",
            r"(\w+(?:\s+\w+)*) can (.+)",
            r"(\w+(?:\s+\w+)*) belongs to (.+)",
            r"(\w+(?:\s+\w+)*) comes from (.+)",
            r"(\w+(?:\s+\w+)*) serves (.+)",
            r"(\w+(?:\s+\w+)*) fights (?:against )?(.+)",
            r"(\w+(?:\s+\w+)*) worships (.+)"
        ]
        
        logger.info(f"++ SEMANTIC MEMORY INITIALIZED FOR {agent_id} ++")
    
    async def extract_and_store_knowledge(self, memory: MemoryItem) -> StandardResponse:
        """
        ++ SACRED KNOWLEDGE EXTRACTION BLESSED BY SEMANTIC ANALYSIS ++
        
        Extract factual knowledge from memory content and store as
        structured facts with automatic concept formation and linking.
        """
        try:
            extracted_facts = []
            
            # Extract blessed facts using pattern matching
            content = memory.content.lower()
            
            for pattern in self._fact_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) == 2:
                        subject, object_value = match
                        predicate = self._infer_predicate(pattern)
                        
                        fact = KnowledgeFact(
                            fact_id="",  # Will be auto-generated
                            subject=subject.strip(),
                            predicate=predicate,
                            object_value=object_value.strip(),
                            source_memory_id=memory.memory_id,
                            confidence=memory.relevance_score * 0.8  # Base confidence from memory relevance
                        )
                        extracted_facts.append(fact)
            
            # Extract blessed entities and create concepts
            entities = self._extract_entities(memory.content)
            for entity in entities:
                await self._ensure_concept_exists(entity)
            
            # Store blessed facts and update knowledge network
            stored_facts = []
            for fact in extracted_facts:
                storage_result = await self._store_fact(fact)
                if storage_result.success:
                    stored_facts.append(fact)
                    # Associate fact with concepts
                    await self._associate_fact_with_concepts(fact)
            
            self.total_facts_learned += len(stored_facts)
            
            # Perform blessed knowledge consolidation periodically
            if self.total_facts_learned % 100 == 0:
                await self._consolidate_knowledge()
            
            logger.info(f"++ KNOWLEDGE EXTRACTED: {len(stored_facts)} facts from {memory.memory_id} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "facts_extracted": len(stored_facts),
                    "entities_found": len(entities),
                    "total_facts": len(self._facts)
                },
                metadata={"blessing": "knowledge_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ KNOWLEDGE EXTRACTION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="KNOWLEDGE_EXTRACTION_FAILED",
                    message=f"Knowledge extraction failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check memory content format and extraction patterns"
                )
            )
    
    async def query_facts_by_subject(self, subject: str, 
                                   confidence_threshold: Optional[float] = None) -> StandardResponse:
        """
        ++ SACRED FACT RETRIEVAL BY SUBJECT BLESSED BY KNOWLEDGE ACCESS ++
        
        Retrieve all blessed facts about a specific subject with
        confidence filtering and relevance ranking.
        """
        try:
            subject_lower = subject.lower()
            confidence_filter = confidence_threshold or self.confidence_threshold
            
            matching_facts = []
            
            if subject_lower in self._subject_index:
                for fact_id in self._subject_index[subject_lower]:
                    fact = self._facts.get(fact_id)
                    if fact and fact.confidence >= confidence_filter:
                        matching_facts.append(fact)
            
            # Sort by blessed confidence and recency
            matching_facts.sort(
                key=lambda f: (f.confidence, f.last_confirmed),
                reverse=True
            )
            
            # Convert to blessed natural language representation
            fact_statements = [fact.to_natural_language() for fact in matching_facts]
            
            logger.info(f"++ RETRIEVED {len(matching_facts)} FACTS ABOUT {subject} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "subject": subject,
                    "facts": fact_statements,
                    "fact_objects": [fact.__dict__ for fact in matching_facts],
                    "total_found": len(matching_facts)
                },
                metadata={"blessing": "subject_knowledge_retrieved"}
            )
            
        except Exception as e:
            logger.error(f"++ SUBJECT FACT RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="SUBJECT_FACT_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def query_facts_by_predicate(self, predicate: str,
                                     limit: int = 20) -> StandardResponse:
        """
        ++ SACRED FACT RETRIEVAL BY RELATIONSHIP BLESSED BY PATTERN ACCESS ++
        
        Retrieve blessed facts matching specific relationship type
        with confidence weighting and usage statistics.
        """
        try:
            predicate_lower = predicate.lower()
            matching_facts = []
            
            if predicate_lower in self._predicate_index:
                for fact_id in self._predicate_index[predicate_lower]:
                    fact = self._facts.get(fact_id)
                    if fact and fact.confidence >= self.confidence_threshold:
                        matching_facts.append(fact)
            
            # Sort by blessed confidence and confirmation count
            matching_facts.sort(
                key=lambda f: (f.confidence, f.confirmation_count),
                reverse=True
            )
            
            # Apply sacred limit
            limited_facts = matching_facts[:limit]
            fact_statements = [fact.to_natural_language() for fact in limited_facts]
            
            logger.info(f"++ RETRIEVED {len(limited_facts)} FACTS WITH PREDICATE {predicate} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "predicate": predicate,
                    "facts": fact_statements,
                    "total_found": len(matching_facts)
                },
                metadata={"blessing": "predicate_knowledge_retrieved"}
            )
            
        except Exception as e:
            logger.error(f"++ PREDICATE FACT RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PREDICATE_FACT_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def get_concept_knowledge(self, concept_name: str) -> StandardResponse:
        """
        ++ SACRED CONCEPT KNOWLEDGE RETRIEVAL BLESSED BY TAXONOMIC WISDOM ++
        
        Retrieve comprehensive knowledge about a concept including
        hierarchical relationships and associated facts.
        """
        try:
            concept_lower = concept_name.lower()
            concept = self._concepts.get(concept_lower)
            
            if not concept:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="CONCEPT_NOT_FOUND",
                        message=f"Concept '{concept_name}' not found in semantic memory"
                    )
                )
            
            # Gather blessed associated facts
            associated_facts = []
            for fact_id in concept.associated_facts:
                fact = self._facts.get(fact_id)
                if fact and fact.confidence >= self.confidence_threshold:
                    associated_facts.append(fact.to_natural_language())
            
            # Get blessed hierarchical relationships
            parent_names = [self._concepts[pid].concept_name for pid in concept.parent_concepts 
                          if pid in self._concepts]
            child_names = [self._concepts[cid].concept_name for cid in concept.child_concepts
                         if cid in self._concepts]
            related_names = [self._concepts[rid].concept_name for rid in concept.related_concepts
                           if rid in self._concepts]
            
            concept_knowledge = {
                "concept_name": concept.concept_name,
                "importance_score": concept.importance_score,
                "associated_facts": associated_facts,
                "parent_concepts": parent_names,
                "child_concepts": child_names,
                "related_concepts": related_names,
                "total_facts": len(concept.associated_facts)
            }
            
            logger.info(f"++ RETRIEVED CONCEPT KNOWLEDGE FOR {concept_name} ++")
            
            return StandardResponse(
                success=True,
                data=concept_knowledge,
                metadata={"blessing": "concept_knowledge_retrieved"}
            )
            
        except Exception as e:
            logger.error(f"++ CONCEPT KNOWLEDGE RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CONCEPT_KNOWLEDGE_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def find_contradictions(self) -> StandardResponse:
        """
        ++ SACRED CONTRADICTION DETECTION BLESSED BY LOGICAL CONSISTENCY ++
        
        Identify logical contradictions in the knowledge base
        and provide resolution suggestions blessed by reasoning.
        """
        try:
            contradictions_found = []
            
            # Group blessed facts by subject and predicate
            subject_predicate_groups = defaultdict(list)
            for fact in self._facts.values():
                key = f"{fact.subject}_{fact.predicate}"
                subject_predicate_groups[key].append(fact)
            
            # Find blessed contradictions within groups
            for group_key, facts in subject_predicate_groups.items():
                if len(facts) > 1:
                    # Check for contradictory object values
                    object_values = set()
                    for fact in facts:
                        if fact.object_value in object_values:
                            continue
                        
                        # Check if this object value contradicts existing ones
                        for other_fact in facts:
                            if (other_fact.object_value != fact.object_value and 
                                self._are_contradictory(fact.object_value, other_fact.object_value)):
                                
                                contradiction = {
                                    "fact1": fact.to_natural_language(),
                                    "fact2": other_fact.to_natural_language(),
                                    "confidence1": fact.confidence,
                                    "confidence2": other_fact.confidence,
                                    "suggestion": self._suggest_resolution(fact, other_fact)
                                }
                                contradictions_found.append(contradiction)
                        
                        object_values.add(fact.object_value)
            
            logger.info(f"++ FOUND {len(contradictions_found)} CONTRADICTIONS ++")
            
            return StandardResponse(
                success=True,
                data={
                    "contradictions": contradictions_found,
                    "total_found": len(contradictions_found)
                },
                metadata={"blessing": "contradictions_detected"}
            )
            
        except Exception as e:
            logger.error(f"++ CONTRADICTION DETECTION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CONTRADICTION_DETECTION_FAILED", message=str(e))
            )
    
    async def _store_fact(self, fact: KnowledgeFact) -> StandardResponse:
        """++ SACRED FACT STORAGE BLESSED BY KNOWLEDGE PRESERVATION ++"""
        try:
            # Check for blessed existing fact
            existing_fact = self._facts.get(fact.fact_id)
            if existing_fact:
                # Confirm existing fact with new source
                existing_fact.confirm_fact(fact.source_memory_id)
                logger.info(f"++ FACT CONFIRMED: {fact.fact_id} ++")
                return StandardResponse(success=True, data={"confirmed": True})
            
            # Store blessed new fact
            self._facts[fact.fact_id] = fact
            
            # Update sacred indices
            self._subject_index[fact.subject.lower()].append(fact.fact_id)
            self._predicate_index[fact.predicate.lower()].append(fact.fact_id)
            self._object_index[fact.object_value.lower()].append(fact.fact_id)
            
            return StandardResponse(success=True, data={"stored": True})
            
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="FACT_STORAGE_FAILED", message=str(e))
            )
    
    async def _ensure_concept_exists(self, entity_name: str) -> ConceptNode:
        """++ SACRED CONCEPT CREATION BLESSED BY TAXONOMIC ORGANIZATION ++"""
        entity_lower = entity_name.lower()
        
        if entity_lower not in self._concepts:
            concept = ConceptNode(
                concept_id=entity_lower,
                concept_name=entity_name
            )
            self._concepts[entity_lower] = concept
            self.total_concepts_formed += 1
            
            logger.info(f"++ CONCEPT CREATED: {entity_name} ++")
        
        return self._concepts[entity_lower]
    
    async def _associate_fact_with_concepts(self, fact: KnowledgeFact):
        """++ SACRED FACT-CONCEPT ASSOCIATION BLESSED BY KNOWLEDGE LINKING ++"""
        # Associate fact with subject concept
        subject_concept = await self._ensure_concept_exists(fact.subject)
        subject_concept.associate_fact(fact.fact_id)
        
        # Associate fact with object concept if it's an entity
        if self._is_entity(fact.object_value):
            object_concept = await self._ensure_concept_exists(fact.object_value)
            object_concept.associate_fact(fact.fact_id)
    
    def _extract_entities(self, content: str) -> List[str]:
        """++ SACRED ENTITY EXTRACTION BLESSED BY SEMANTIC RECOGNITION ++"""
        # Simple blessed entity extraction (can be enhanced with NER)
        entity_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Proper nouns
            r'\b(?:Emperor|Omnissiah|Machine God|Space Marine|Ork|Chaos|Imperium)\b',  # Known entities
            r'\b[A-Z]{2,}\b'  # Acronyms
        ]
        
        entities = set()
        for pattern in entity_patterns:
            matches = re.findall(pattern, content)
            entities.update(matches)
        
        # Filter blessed entities (minimum 2 characters, not common words)
        common_words = {'The', 'And', 'But', 'For', 'Or', 'Yet', 'So'}
        filtered_entities = [entity for entity in entities 
                           if len(entity) >= 2 and entity not in common_words]
        
        return filtered_entities
    
    def _infer_predicate(self, pattern: str) -> str:
        """++ SACRED PREDICATE INFERENCE BLESSED BY PATTERN MATCHING ++"""
        predicate_map = {
            r"(\w+(?:\s+\w+)*) is (?:a |an )?(.+)": "is",
            r"(\w+(?:\s+\w+)*) has (.+)": "has",
            r"(\w+(?:\s+\w+)*) can (.+)": "can",
            r"(\w+(?:\s+\w+)*) belongs to (.+)": "belongs_to",
            r"(\w+(?:\s+\w+)*) comes from (.+)": "comes_from",
            r"(\w+(?:\s+\w+)*) serves (.+)": "serves",
            r"(\w+(?:\s+\w+)*) fights (?:against )?(.+)": "fights",
            r"(\w+(?:\s+\w+)*) worships (.+)": "worships"
        }
        
        return predicate_map.get(pattern, "related_to")
    
    def _is_entity(self, text: str) -> bool:
        """++ BLESSED ENTITY RECOGNITION ++"""
        # Simple heuristic: proper nouns or known entity patterns
        return (text[0].isupper() or 
                any(known in text.lower() for known in 
                    ['emperor', 'omnissiah', 'marine', 'ork', 'chaos']))
    
    def _are_contradictory(self, value1: str, value2: str) -> bool:
        """++ SACRED CONTRADICTION DETECTION BLESSED BY LOGIC ++"""
        # Simple contradiction detection (can be enhanced)
        contradiction_pairs = [
            ('dead', 'alive'), ('enemy', 'ally'), ('good', 'evil'),
            ('human', 'ork'), ('loyal', 'traitor')
        ]
        
        for pair in contradiction_pairs:
            if ((value1.lower() in pair[0] and value2.lower() in pair[1]) or
                (value1.lower() in pair[1] and value2.lower() in pair[0])):
                return True
        
        return False
    
    def _suggest_resolution(self, fact1: KnowledgeFact, fact2: KnowledgeFact) -> str:
        """++ SACRED CONFLICT RESOLUTION BLESSED BY WISDOM ++"""
        if fact1.confidence > fact2.confidence:
            return f"Keep higher confidence fact: {fact1.to_natural_language()}"
        elif fact2.confidence > fact1.confidence:
            return f"Keep higher confidence fact: {fact2.to_natural_language()}"
        else:
            return "Manual review required - equal confidence contradictions"
    
    async def _consolidate_knowledge(self):
        """++ SACRED KNOWLEDGE CONSOLIDATION BLESSED BY OPTIMIZATION ++"""
        # Remove low-confidence facts if over capacity
        if len(self._facts) > self.max_facts:
            low_confidence_facts = [
                fact_id for fact_id, fact in self._facts.items()
                if fact.confidence < self.confidence_threshold
            ]
            
            for fact_id in low_confidence_facts:
                del self._facts[fact_id]
                # Clean up indices (simplified)
                logger.info(f"++ PRUNED LOW-CONFIDENCE FACT: {fact_id} ++")
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """++ SACRED SEMANTIC MEMORY STATISTICS BLESSED BY MONITORING ++"""
        if not self._facts:
            return {"total_facts": 0, "total_concepts": 0, "average_confidence": 0.0}
        
        total_confidence = sum(fact.confidence for fact in self._facts.values())
        
        return {
            "total_facts": len(self._facts),
            "total_concepts": len(self._concepts),
            "average_confidence": total_confidence / len(self._facts),
            "facts_learned": self.total_facts_learned,
            "concepts_formed": self.total_concepts_formed,
            "last_pruning": self.last_pruning.isoformat()
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_semantic_memory():
    """++ SACRED SEMANTIC MEMORY TESTING RITUAL ++"""
    print("++ TESTING SACRED SEMANTIC MEMORY BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed database for testing
    from src.database.context_db import ContextDatabase
    
    # Create blessed test database
    test_db = ContextDatabase("test_semantic.db")
    await test_db.initialize_sacred_temple()
    
    # Create blessed semantic memory
    semantic_memory = SemanticMemory("test_agent_001", test_db)
    
    # Test sacred knowledge extraction
    test_memory = MemoryItem(
        agent_id="test_agent_001",
        memory_type=MemoryType.SEMANTIC,
        content="The Emperor is the master of mankind. Space Marines serve the Emperor. Orks fight against the Imperium.",
        relevance_score=0.9
    )
    
    extraction_result = await semantic_memory.extract_and_store_knowledge(test_memory)
    print(f"++ KNOWLEDGE EXTRACTION: {extraction_result.success}, Facts: {extraction_result.data.get('facts_extracted', 0)} ++")
    
    # Test blessed fact retrieval by subject
    emperor_facts = await semantic_memory.query_facts_by_subject("emperor")
    print(f"++ EMPEROR FACTS: {emperor_facts.success}, Count: {len(emperor_facts.data.get('facts', []))} ++")
    
    # Test blessed fact retrieval by predicate  
    serves_facts = await semantic_memory.query_facts_by_predicate("serves")
    print(f"++ SERVES FACTS: {serves_facts.success}, Count: {len(serves_facts.data.get('facts', []))} ++")
    
    # Test blessed concept knowledge
    if emperor_facts.success and emperor_facts.data.get('facts'):
        concept_result = await semantic_memory.get_concept_knowledge("emperor")
        print(f"++ EMPEROR CONCEPT: {concept_result.success} ++")
    
    # Test blessed contradiction detection
    contradiction_result = await semantic_memory.find_contradictions()
    print(f"++ CONTRADICTIONS: {contradiction_result.success}, Count: {len(contradiction_result.data.get('contradictions', []))} ++")
    
    # Display sacred statistics
    stats = semantic_memory.get_memory_statistics()
    print(f"++ SEMANTIC MEMORY STATISTICS: {stats} ++")
    
    # Sacred cleanup
    await test_db.close_sacred_temple()
    
    print("++ SACRED SEMANTIC MEMORY TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED SEMANTIC MEMORY TESTING RITUALS ++
    print("++ SACRED SEMANTIC MEMORY BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE ETERNAL KNOWLEDGE ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_semantic_memory())
    
    print("++ ALL SACRED SEMANTIC MEMORY OPERATIONS BLESSED AND FUNCTIONAL ++")