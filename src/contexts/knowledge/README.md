# Knowledge Context

## Overview
The Knowledge Context provides intelligent information retrieval and management for the Novel Engine platform. It implements a hybrid RAG (Retrieval-Augmented Generation) system combining vector search, BM25 keyword matching, and knowledge graph traversal.

This context handles document ingestion, entity extraction, semantic search, context assembly for AI prompts, and knowledge base maintenance. It enables characters and systems to "remember" and "recall" information contextually.

## Domain

### Aggregates
- **KnowledgeBase**: Root aggregate for domain knowledge
  - Manages documents, entities, and relationships
  - Version control for knowledge evolution
  - Access control integration

### Entities
- **Document**: Ingested knowledge source
  - Content, metadata, extraction status
  - Chunking strategy selection
  
- **ExtractedEntity**: Discovered entity from content
  - Type: CHARACTER, LOCATION, ITEM, EVENT, ORGANIZATION
  - Relationships to other entities
  - Confidence scoring

### Value Objects
- **KnowledgeItem**: Specific piece of knowledge
  - Subject, predicate, object format
  - Certainty level: CERTAIN, LIKELY, POSSIBLE, SPECULATED, MINIMAL
  - Source attribution
  
- **DocumentChunk**: Processed document segment
  - Vector embedding
  - Position tracking
  - Overlap management
  
- **RetrievalResult**: Search result with relevance
  - Content, source, similarity score
  - Token count for budget management
  
- **ExtractionConfig**: Entity extraction parameters
  - Confidence threshold, max entities
  - Relationship extraction toggle

### Domain Events
- **DocumentIngested**: New document added
- **EntityExtracted**: New entity discovered
- **KnowledgeUpdated**: Information changed
- **ContextAssembled**: Retrieved context for query

## Application

### Services
- **EntityExtractionService**: LLM-based entity discovery
  - `extract(text, config)` - Extract entities from narrative
  - `extract_with_relationships(text, config)` - Include relationships
  - `extract_batch(texts, config)` - Process multiple documents
  - `extract_large_text(text, config, chunk_size, overlap)` - Handle long texts
  - Relationship types: KNOWS, KILLED, LOVES, HATES, PARENT_OF, MEMBER_OF, etc.

- **ContextOptimizer**: RAG context assembly
  - `assemble_context(query, knowledge_base_id)` - Retrieve relevant info
  - Token budget management
  - Relevance ranking and deduplication
  
- **BM25Retriever**: Keyword-based retrieval
  - Classic BM25 algorithm implementation
  - Hybrid search with vector results

- **CitationFormatter**: Source attribution
  - Format retrieved context with citations
  - Support multiple citation styles

- **CoreferenceResolutionService**: Resolve pronouns/references
  - Link "he/she/it" to proper entities
  - Maintain entity consistency

### Ports (Interfaces)
- **ILLMClient**: LLM interface for extraction
- **IVectorStore**: Vector database abstraction
- **IGraphStore**: Knowledge graph storage
- **IChunkingStrategy**: Document chunking interface
- **IEmbeddingService**: Text embedding generation
- **IReranker**: Result relevance ranking

### Commands
- **IngestDocument**: Add document to knowledge base
  - Handler: `IngestDocumentHandler`
  - Side effects: Entity extraction, chunking, embedding
  
- **ExtractEntities**: Run entity extraction on content
  - Handler: `ExtractEntitiesHandler`

### Queries
- **SearchKnowledge**: Semantic search
  - Handler: `SearchKnowledgeHandler`
  - Performance: Vector index + optional BM25 hybrid
  
- **GetEntityRelations**: Knowledge graph traversal
  - Handler: `GetEntityRelationsHandler`

## Infrastructure

### Repospositories
- **KnowledgeRepository**: Document and entity storage
  - Implementation: PostgreSQL + pgvector for embeddings
  
- **VectorStore**: Semantic search index
  - Implementation: pgvector or dedicated vector DB

### External Services
- **EmbeddingCacheService**: Embedding result caching
- **ContextWindowManager**: Token budget enforcement

## API

### REST Endpoints
- `POST /api/knowledge/documents` - Ingest document
- `GET /api/knowledge/search` - Semantic search
- `GET /api/knowledge/entities/{id}` - Get entity details
- `GET /api/knowledge/entities/{id}/relations` - Get relationships
- `POST /api/knowledge/extract` - Extract entities from text

### WebSocket Events
- `knowledge.document_ingested` - Ingestion progress
- `knowledge.entity_extracted` - New entity notification

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/knowledge/unit/ -v

# Integration tests
pytest tests/contexts/knowledge/integration/ -v

# All context tests
pytest tests/contexts/knowledge/ -v
```

### Test Coverage
Current coverage: 65%
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Hybrid RAG (vector + BM25) for retrieval
- ADR-002: LLM-based entity extraction
- ADR-003: Knowledge graph for relationship tracking

## Integration Points

### Inbound
- Events consumed:
  - `NarrativeGenerated` from Narrative Context (auto-ingest)
  - `WorldStateChanged` from World Context (entity updates)

### Outbound
- Events published:
  - `EntityExtracted` - For world/character updates
  - `ContextAssembled` - For AI prompt preparation

### Dependencies
- **Domain**: None (pure domain)
- **Application**: AI Context (LLM calls)
- **Infrastructure**: PostgreSQL + pgvector, optional dedicated vector DB

## Development Guide

### Adding New Features
1. Extend domain models for new knowledge types
2. Add service methods for new retrieval strategies
3. Implement port interfaces for new backends
4. Update API endpoints
5. Write tests

### Common Tasks
- **Adding entity types**: Extend `EntityType` enum and extraction prompts
- **Adding relationship types**: Extend `RelationshipType` enum
- **New retrieval strategy**: Implement `IKnowledgeRetriever` interface

## Maintainer
Team: @knowledge-team
Contact: knowledge@example.com
