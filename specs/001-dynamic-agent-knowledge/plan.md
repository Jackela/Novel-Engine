# Implementation Plan: Dynamic Agent Knowledge and Context System

**Branch**: `001-dynamic-agent-knowledge` | **Date**: 2025-11-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-dynamic-agent-knowledge/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace static file-based (Markdown) context engineering system with a dynamic, centralized, permission-controlled knowledge base. Game Masters will manage agent knowledge (profiles, objectives, memories, world lore) through an Admin API and Web UI, replacing manual Markdown file editing. AI agents will automatically retrieve current, permission-filtered knowledge during simulation turns via the SubjectiveBriefPhase integration.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (backend API), React 18+ (frontend Web UI), PostgreSQL (knowledge entry storage), Kafka (event bus), pytest (testing)  
**Storage**: PostgreSQL as Single Source of Truth (SSOT) for knowledge entries; no Redis caching for MVP (per Constitution Article IV)  
**Testing**: pytest with TDD Red-Green-Refactor cycle; coverage targets per Article III (Domain ≥80%, Application ≥70%, Infrastructure ≥60%)  
**Target Platform**: Linux server (backend), modern web browsers (frontend)  
**Project Type**: Web application (backend API + frontend Web UI)  
**Performance Goals**: Knowledge retrieval <500ms for ≤100 entries (SC-002), Admin operations <30s (SC-001), 99.9% availability (SC-006)  
**Constraints**: Zero data loss during migration (SC-007), 100% access control enforcement (SC-004), no Markdown file reads for migrated agents (SC-003)  
**Scale/Scope**: Support ≥10,000 knowledge entries (SC-008), all existing agents migrated within 1 hour (SC-007), immediate context updates (SC-005)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Article I - Domain-Driven Design (DDD)**: ✅ New bounded context "Knowledge Management" (`contexts/knowledge/`). Domain models: KnowledgeEntry (aggregate root), AccessControlRule (value object), AgentContext (aggregate). Domain layer will be pure with NO direct file I/O, database access, or LLM dependencies. All infrastructure concerns delegated to adapters.

- **Article II - Ports & Adapters**: ✅ Ports to define: IKnowledgeRepository (CRUD operations), IKnowledgeRetriever (query interface), IAccessControlService (permission checking), IContextAssembler (agent context building). Adapters to create: PostgreSQLKnowledgeRepository (persistence), MarkdownMigrationAdapter (legacy file migration), SubjectiveBriefPhaseAdapter (turn integration). Dependency inversion: application layer depends on domain ports, infrastructure provides adapters.

- **Article III - Test-Driven Development (TDD)**: ✅ Red-Green-Refactor plan: (1) Write failing unit tests for KnowledgeEntry aggregate, (2) Implement domain model, (3) Write failing tests for AccessControlRule filtering, (4) Implement access control logic, (5) Write failing tests for IKnowledgeRepository operations, (6) Implement PostgreSQL adapter, (7) Write failing integration tests for SubjectiveBriefPhase, (8) Implement turn integration. Coverage targets: Domain ≥80%, Application ≥70%, Infrastructure ≥60%.

- **Article IV - Single Source of Truth (SSOT)**: ✅ PostgreSQL is authoritative SSOT for all knowledge entries. Markdown files become read-only archive after migration. NO Redis caching for MVP to ensure consistency and simplicity. During migration phase: dual-read (knowledge base + markdown fallback) with knowledge base taking precedence. Post-migration: knowledge base is sole source (FR-006).

- **Article V - SOLID Principles**: ✅ SRP - KnowledgeEntry manages knowledge data only, AccessControlRule handles permissions only. OCP - New knowledge types added via enum extension without modifying core retrieval logic. LSP - All repository implementations must be substitutable through IKnowledgeRepository interface. ISP - Separate read (IKnowledgeRetriever) and write (IKnowledgeRepository) interfaces. DIP - SubjectiveBriefPhase depends on IKnowledgeRetriever abstraction, not concrete PostgreSQL implementation.

- **Article VI - Event-Driven Architecture (EDA)**: ✅ Domain events to publish: KnowledgeEntryCreated, KnowledgeEntryUpdated, KnowledgeEntryDeleted. Events published to Kafka for: (1) audit logging, (2) future cache invalidation (post-MVP), (3) notification systems. NO synchronous cross-context calls - all integration via events. Event schemas defined in contracts/ for subscriber compatibility.

- **Article VII - Observability**: ✅ Structured logging: all CRUD operations with correlation IDs, character context, and user IDs. Prometheus metrics: `knowledge_entry_created_total`, `knowledge_entry_updated_total`, `knowledge_entry_deleted_total`, `knowledge_retrieval_duration_seconds`, `knowledge_retrieval_count_total`, `access_denied_total`, `migration_entries_processed_total`. OpenTelemetry tracing: trace knowledge retrieval calls during SubjectiveBriefPhase with agent_id and turn_number spans.

- **Constitution Compliance Review Date**: 2025-11-04 (no violations, greenfield feature with full constitutional alignment)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
contexts/knowledge/                    # New bounded context for Knowledge Management
├── domain/
│   ├── models/
│   │   ├── knowledge_entry.py        # Aggregate root
│   │   ├── agent_context.py          # Aggregate
│   │   └── access_control_rule.py    # Value object
│   ├── events/
│   │   ├── knowledge_entry_created.py
│   │   ├── knowledge_entry_updated.py
│   │   └── knowledge_entry_deleted.py
│   └── services/
│       └── access_control_service.py # Domain service for permission checking
├── application/
│   ├── ports/
│   │   ├── i_knowledge_repository.py    # Port for persistence
│   │   ├── i_knowledge_retriever.py     # Port for queries
│   │   ├── i_access_control_service.py  # Port for permissions
│   │   └── i_context_assembler.py       # Port for context assembly
│   └── use_cases/
│       ├── create_knowledge_entry.py
│       ├── update_knowledge_entry.py
│       ├── delete_knowledge_entry.py
│       ├── retrieve_agent_context.py
│       └── migrate_markdown_files.py
└── infrastructure/
    ├── repositories/
    │   └── postgresql_knowledge_repository.py  # PostgreSQL adapter
    ├── adapters/
    │   ├── markdown_migration_adapter.py       # Legacy file migration
    │   └── subjective_brief_phase_adapter.py   # Turn integration
    └── events/
        └── kafka_event_publisher.py            # Event publishing

backend/api/
├── routes/
│   └── knowledge.py                   # Admin API endpoints (RESTful/GraphQL)
└── middleware/
    └── auth_middleware.py             # Novel Engine authentication integration

frontend/admin/knowledge/              # Web UI for Game Masters
├── components/
│   ├── KnowledgeEntryForm.tsx        # Create/edit knowledge entries
│   ├── KnowledgeEntryList.tsx        # Browse all entries
│   └── AccessControlPanel.tsx        # Manage permissions
└── pages/
    └── KnowledgeManagementPage.tsx   # Main admin page

tests/
├── unit/knowledge/
│   ├── test_knowledge_entry.py       # Domain model tests
│   ├── test_access_control_rule.py
│   └── test_access_control_service.py
├── integration/knowledge/
│   ├── test_postgresql_repository.py # Repository integration tests
│   └── test_subjective_brief_integration.py
└── contract/knowledge/
    └── test_admin_api_contract.py    # API contract tests
```

**Structure Decision**: Web application structure selected. Backend uses DDD hexagonal architecture in `contexts/knowledge/` with domain, application (ports + use cases), and infrastructure (adapters) layers. Frontend adds new route `frontend/admin/knowledge` for Game Master Web UI. Admin API integrated into existing `backend/api/` with authentication middleware. Tests follow three-tier structure (unit for domain, integration for adapters, contract for API).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations identified. This is a greenfield feature with full constitutional alignment. All complexity is justified by constitutional requirements (DDD, hexagonal architecture, TDD, SSOT, SOLID, EDA, observability).
