"""
Knowledge Management Bounded Context

This context handles centralized agent knowledge and context assembly,
replacing the static Markdown file-based system with a dynamic, 
permission-controlled knowledge base.

Domain Models:
- KnowledgeEntry (aggregate root)
- AccessControlRule (value object)
- AgentContext (aggregate)

Ports:
- IKnowledgeRepository
- IKnowledgeRetriever
- IAccessControlService
- IContextAssembler

Constitution Compliance:
- Article I (DDD): Pure domain models, no infrastructure dependencies
- Article II (Hexagonal): Ports & Adapters architecture
- Article III (TDD): Test-driven development with ≥80% domain coverage
- Article IV (SSOT): PostgreSQL as authoritative source
"""
