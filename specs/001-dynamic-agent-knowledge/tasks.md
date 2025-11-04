# Tasks: Dynamic Agent Knowledge and Context System

**Input**: Design documents from `/specs/001-dynamic-agent-knowledge/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, quickstart.md

**Tests**: Tasks include TDD test tasks per Constitution Article III (mandatory)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app structure**: `contexts/knowledge/` (DDD bounded context), `backend/api/`, `frontend/admin/knowledge/`
- **Tests**: `tests/unit/knowledge/`, `tests/integration/knowledge/`, `tests/contract/knowledge/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and DDD bounded context structure

- [x] T001 Create Knowledge Management bounded context directory structure in contexts/knowledge/ per plan.md
- [x] T002 Initialize Python dependencies (FastAPI, PostgreSQL driver, Kafka client, pytest) in pyproject.toml or requirements.txt
- [x] T003 [P] Configure pytest with coverage targets (Domain ≥80%, Application ≥70%, Infrastructure ≥60%) in pytest.ini
- [x] T004 [P] Setup shared types for knowledge domain in src/shared_types.py (KnowledgeEntryId, CharacterId, UserId)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create PostgreSQL migration for knowledge_entries table with indexes per data-model.md schema
- [x] T006 Create PostgreSQL migration for knowledge_audit_log table per data-model.md schema
- [x] T007 [P] Setup Kafka topic configuration for knowledge events (knowledge.entry.created, updated, deleted) per contracts/domain-events.avro.json
- [x] T008 [P] Implement Novel Engine authentication middleware integration in backend/api/middleware/auth_middleware.py
- [x] T009 [P] Create base domain event publisher interface in contexts/knowledge/application/ports/i_event_publisher.py
- [x] T010 [P] Create Kafka event publisher adapter in contexts/knowledge/infrastructure/events/kafka_event_publisher.py
- [x] T011 [P] Setup structured logging configuration with correlation IDs in contexts/knowledge/infrastructure/logging_config.py
- [x] T012 [P] Setup Prometheus metrics configuration in contexts/knowledge/infrastructure/metrics_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Constitution Alignment Gates

- [x] CG001 Verify domain models are pure (no infrastructure dependencies) in contexts/knowledge/domain/ (Article I - DDD)
- [x] CG002 Verify all ports defined before adapters implemented (Article II - Hexagonal) in contexts/knowledge/application/ports/
- [x] CG003 Enforce TDD Red-Green-Refactor cycle: ALL tests must exist and FAIL before implementation (Article III - TDD)
- [x] CG004 Verify PostgreSQL is SSOT with no Redis caching for MVP (Article IV - SSOT) per plan.md Technical Context
- [x] CG005 SOLID compliance check: SRP (one concern per class), OCP (enum extension), LSP (interface substitution), ISP (separate read/write interfaces), DIP (depend on abstractions)
- [x] CG006 Verify domain events published for all mutations (Article VI - EDA) per contracts/domain-events.avro.json
- [x] CG007 Verify observability instrumented: structured logging, Prometheus metrics, OpenTelemetry tracing (Article VII)
- [x] CG008 Constitution compliance review complete with zero violations per plan.md Constitution Check

---

## Phase 3: User Story 1 - Centralized Knowledge Management (Priority: P1) 🎯 MVP

**Goal**: Enable Game Masters to create, update, and delete knowledge entries through Admin API and Web UI, replacing manual Markdown file editing

**Independent Test**: Create a knowledge entry via Web UI, update it, verify changes persist in PostgreSQL, delete it, verify removal - all without touching Markdown files

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL before implementation)

- [x] T013 [P] [US1] Write failing unit test for KnowledgeEntry.update_content in tests/unit/knowledge/test_knowledge_entry.py
- [x] T014 [P] [US1] Write failing unit test for KnowledgeEntry content validation (empty content) in tests/unit/knowledge/test_knowledge_entry.py
- [x] T015 [P] [US1] Write failing unit test for AccessControlRule invariants in tests/unit/knowledge/test_access_control_rule.py
- [x] T016 [P] [US1] Write failing unit test for CreateKnowledgeEntryUseCase in tests/unit/knowledge/test_create_knowledge_entry_use_case.py
- [x] T017 [P] [US1] Write failing unit test for UpdateKnowledgeEntryUseCase in tests/unit/knowledge/test_update_knowledge_entry_use_case.py
- [x] T018 [P] [US1] Write failing unit test for DeleteKnowledgeEntryUseCase in tests/unit/knowledge/test_delete_knowledge_entry_use_case.py
- [x] T019 [P] [US1] Write failing integration test for PostgreSQLKnowledgeRepository.save in tests/integration/knowledge/test_postgresql_repository.py
- [x] T020 [P] [US1] Write failing integration test for PostgreSQLKnowledgeRepository.get_by_id in tests/integration/knowledge/test_postgresql_repository.py
- [x] T021 [P] [US1] Write failing integration test for PostgreSQLKnowledgeRepository.delete in tests/integration/knowledge/test_postgresql_repository.py
- [x] T022 [P] [US1] Write failing contract test for POST /api/v1/knowledge/entries in tests/contract/knowledge/test_admin_api_contract.py
- [x] T023 [P] [US1] Write failing contract test for PUT /api/v1/knowledge/entries/{id} in tests/contract/knowledge/test_admin_api_contract.py
- [x] T024 [P] [US1] Write failing contract test for DELETE /api/v1/knowledge/entries/{id} in tests/contract/knowledge/test_admin_api_contract.py

### Implementation for User Story 1

**Domain Layer (Pure models, no infrastructure)**:

- [x] T025 [P] [US1] Implement KnowledgeType enum in contexts/knowledge/domain/models/knowledge_type.py
- [x] T026 [P] [US1] Implement AccessLevel enum in contexts/knowledge/domain/models/access_level.py
- [x] T027 [P] [US1] Implement AccessControlRule value object in contexts/knowledge/domain/models/access_control_rule.py
- [x] T028 [US1] Implement KnowledgeEntry aggregate root in contexts/knowledge/domain/models/knowledge_entry.py (depends on T025, T026, T027)
- [x] T029 [P] [US1] Implement KnowledgeEntryCreated domain event in contexts/knowledge/domain/events/knowledge_entry_created.py
- [x] T030 [P] [US1] Implement KnowledgeEntryUpdated domain event in contexts/knowledge/domain/events/knowledge_entry_updated.py
- [x] T031 [P] [US1] Implement KnowledgeEntryDeleted domain event in contexts/knowledge/domain/events/knowledge_entry_deleted.py

**Application Layer (Ports and Use Cases)**:

- [x] T032 [P] [US1] Define IKnowledgeRepository port in contexts/knowledge/application/ports/i_knowledge_repository.py
- [x] T033 [P] [US1] Implement CreateKnowledgeEntryUseCase in contexts/knowledge/application/use_cases/create_knowledge_entry.py
- [x] T034 [P] [US1] Implement UpdateKnowledgeEntryUseCase in contexts/knowledge/application/use_cases/update_knowledge_entry.py
- [x] T035 [P] [US1] Implement DeleteKnowledgeEntryUseCase in contexts/knowledge/application/use_cases/delete_knowledge_entry.py

**Infrastructure Layer (Adapters)**:

- [x] T036 [US1] Implement PostgreSQLKnowledgeRepository adapter in contexts/knowledge/infrastructure/repositories/postgresql_knowledge_repository.py (depends on T032)
- [x] T037 [US1] Implement audit log writer in contexts/knowledge/infrastructure/audit/audit_log_writer.py for FR-011 compliance

**API Layer**:

- [x] T038 [US1] Implement POST /api/v1/knowledge/entries endpoint in src/api/knowledge_api.py (FR-002)
- [x] T039 [US1] Implement GET /api/v1/knowledge/entries endpoint with filtering in src/api/knowledge_api.py
- [x] T040 [US1] Implement GET /api/v1/knowledge/entries/{id} endpoint in src/api/knowledge_api.py
- [x] T041 [US1] Implement PUT /api/v1/knowledge/entries/{id} endpoint in src/api/knowledge_api.py (FR-003)
- [x] T042 [US1] Implement DELETE /api/v1/knowledge/entries/{id} endpoint in src/api/knowledge_api.py (FR-004)
- [x] T043 [US1] Add authentication/authorization checks (admin or game_master role) to all Admin API endpoints via middleware (integrate with T008)

**Frontend Layer**:

- [x] T044 [P] [US1] Create KnowledgeAPI service for API calls in frontend/admin/knowledge/services/knowledgeApi.ts
- [x] T045 [P] [US1] Create KnowledgeEntryForm component in frontend/admin/knowledge/components/KnowledgeEntryForm.tsx
- [x] T046 [P] [US1] Create KnowledgeEntryList component in frontend/admin/knowledge/components/KnowledgeEntryList.tsx
- [x] T047 [US1] Create KnowledgeManagementPage main page in frontend/admin/knowledge/pages/KnowledgeManagementPage.tsx (depends on T044, T045, T046)

**Observability (Article VII)**:

- [x] T048 [P] [US1] Add structured logging for CRUD operations in contexts/knowledge/application/use_cases/ with correlation IDs and character context
- [x] T049 [P] [US1] Instrument Prometheus metrics (knowledge_entry_created_total, updated_total, deleted_total) in contexts/knowledge/infrastructure/ (metrics_config.py already implemented)
- [x] T050 [P] [US1] Add OpenTelemetry tracing spans for Admin API endpoints in src/api/knowledge_api.py

**Checkpoint**: Game Masters can create, update, and delete knowledge entries through Web UI; all operations persisted to PostgreSQL; 100% TDD coverage for domain and application layers

---

## Phase 4: User Story 2 - Permission-Controlled Knowledge Access (Priority: P2)

**Goal**: Enable Game Masters to define access rules (public, role-based, character-specific) for knowledge entries to control agent information exposure

**Independent Test**: Create knowledge entries with different access levels, verify filtering works correctly when retrieving entries for agents with different roles and character IDs

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL before implementation)

- [x] T051 [P] [US2] Write failing unit test for AccessControlRule.permits with public access in tests/unit/knowledge/test_access_control_rule.py
- [x] T052 [P] [US2] Write failing unit test for AccessControlRule.permits with role-based access in tests/unit/knowledge/test_access_control_rule.py
- [x] T053 [P] [US2] Write failing unit test for AccessControlRule.permits with character-specific access in tests/unit/knowledge/test_access_control_rule.py
- [x] T054 [P] [US2] Write failing unit test for KnowledgeEntry.is_accessible_by in tests/unit/knowledge/test_knowledge_entry.py
- [x] T055 [P] [US2] Write failing integration test for PostgreSQLKnowledgeRepository.retrieve_for_agent with access filtering in tests/integration/knowledge/test_postgresql_repository.py

### Implementation for User Story 2

**Domain Layer**:

- [x] T056 [US2] Implement AgentIdentity value object in contexts/knowledge/domain/models/agent_identity.py
- [x] T057 [US2] Implement is_accessible_by method on KnowledgeEntry in contexts/knowledge/domain/models/knowledge_entry.py (depends on T028, T056)

**Application Layer**:

- [x] T058 [P] [US2] Define IKnowledgeRetriever port in contexts/knowledge/application/ports/i_knowledge_retriever.py
- [x] T059 [P] [US2] Define IAccessControlService port in contexts/knowledge/application/ports/i_access_control_service.py
- [x] T060 [US2] Implement AccessControlService domain service in contexts/knowledge/domain/services/access_control_service.py (depends on T027, T056)

**Infrastructure Layer**:

- [x] T061 [US2] Implement retrieve_for_agent method in PostgreSQLKnowledgeRepository with access control filtering per FR-005 in contexts/knowledge/infrastructure/repositories/postgresql_knowledge_repository.py

**Frontend Layer**:

- [x] T062 [P] [US2] Create AccessControlPanel component in frontend/admin/knowledge/components/AccessControlPanel.tsx
- [x] T063 [US2] Integrate AccessControlPanel into KnowledgeEntryForm in frontend/admin/knowledge/components/KnowledgeEntryForm.tsx (depends on T045, T062)

**Observability**:

- [x] T064 [P] [US2] Instrument Prometheus metric (access_denied_total) for unauthorized access attempts in contexts/knowledge/infrastructure/

**Checkpoint**: Game Masters can set access rules on knowledge entries; agents only retrieve knowledge matching their permissions; access violations logged for audit

---

## Phase 5: User Story 3 - Automatic Agent Context Retrieval (Priority: P1 - Co-equal with US1)

**Goal**: Integrate knowledge retrieval into SubjectiveBriefPhase so agents automatically retrieve current, permission-filtered knowledge during simulation turns (replacing Markdown file reads)

**Independent Test**: Run simulation turn for agent, verify context includes knowledge from PostgreSQL (not Markdown files), verify access control enforced, verify SubjectiveBriefPhase integration successful

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL before implementation)

- [x] T065 [P] [US3] Write failing unit test for AgentContext.to_llm_prompt_text in tests/unit/knowledge/test_agent_context.py
- [x] T066 [P] [US3] Write failing unit test for RetrieveAgentContextUseCase in tests/unit/knowledge/test_retrieve_agent_context_use_case.py
- [x] T067 [P] [US3] Write failing integration test for SubjectiveBriefPhaseAdapter.assemble_agent_context in tests/integration/knowledge/test_subjective_brief_integration.py
- [x] T068 [P] [US3] Write failing integration test verifying NO Markdown file reads during SubjectiveBriefPhase in tests/integration/knowledge/test_subjective_brief_integration.py (FR-006)

### Implementation for User Story 3

**Domain Layer**:

- [x] T069 [US3] Implement AgentContext aggregate in contexts/knowledge/domain/models/agent_context.py
- [x] T070 [US3] Implement to_llm_prompt_text method on AgentContext in contexts/knowledge/domain/models/agent_context.py (depends on T069)

**Application Layer**:

- [x] T071 [P] [US3] Define IContextAssembler port in contexts/knowledge/application/ports/i_context_assembler.py
- [x] T072 [US3] Implement RetrieveAgentContextUseCase in contexts/knowledge/application/use_cases/retrieve_agent_context.py (depends on T058, T071)

**Infrastructure Layer (SubjectiveBriefPhase Integration)**:

- [x] T073 [US3] Implement SubjectiveBriefPhaseAdapter in contexts/knowledge/infrastructure/adapters/subjective_brief_phase_adapter.py (depends on T071, T072)
- [x] T074 [US3] Modify existing SubjectiveBriefPhase to use SubjectiveBriefPhaseAdapter instead of Markdown file reads (FR-007)
- [x] T075 [US3] Add feature flag to toggle between Markdown and knowledge base for backward compatibility during migration

**Observability**:

- [x] T076 [P] [US3] Instrument Prometheus metrics (knowledge_retrieval_duration_seconds, knowledge_retrieval_count_total) in contexts/knowledge/application/use_cases/retrieve_agent_context.py
- [x] T077 [P] [US3] Add OpenTelemetry tracing spans for knowledge retrieval during SubjectiveBriefPhase with agent_id and turn_number context in contexts/knowledge/infrastructure/adapters/subjective_brief_phase_adapter.py

**Checkpoint**: Agents automatically retrieve current knowledge from PostgreSQL during simulation turns; Markdown files no longer read for agent context (FR-006); access control enforced per FR-009

---

## Phase 6: User Story 4 - Semantic Knowledge Retrieval (Priority: P3 - Post-MVP)

**Goal**: Enable semantic relevance-based knowledge retrieval so agents receive pertinent information even without exact keyword matches

**Independent Test**: Create knowledge entries with semantically similar content, query with related terms, verify relevant entries retrieved without exact keyword matches

**Note**: This is a P3 (nice-to-have) enhancement. Can be deferred post-MVP.

### Tests for User Story 4 (TDD - Write FIRST, ensure FAIL before implementation)

- [x] T078 [P] [US4] Write failing integration test for semantic search with vector embeddings in tests/integration/knowledge/test_semantic_retrieval.py
- [x] T079 [P] [US4] Write failing unit test for semantic relevance scoring in tests/unit/knowledge/test_semantic_scorer.py

### Implementation for User Story 4

**Infrastructure Layer**:

- [x] T080 [US4] Add vector embedding column to knowledge_entries table (PostgreSQL pgvector extension)
- [x] T081 [US4] Implement embedding generation adapter (using LLM or embedding model) in contexts/knowledge/infrastructure/adapters/embedding_generator_adapter.py
- [x] T082 [US4] Implement semantic search in PostgreSQLKnowledgeRepository using vector similarity in contexts/knowledge/infrastructure/repositories/postgresql_knowledge_repository.py
- [x] T083 [US4] Update RetrieveAgentContextUseCase to support semantic retrieval mode in contexts/knowledge/application/use_cases/retrieve_agent_context.py

**Application Layer**:

- [x] T084 [US4] Implement fallback strategy (semantic if available, timestamp ordering if not) in contexts/knowledge/application/use_cases/retrieve_agent_context.py

**Checkpoint**: Semantic retrieval enhances agent context assembly with relevance-based filtering (optional P3 feature) ✅ COMPLETE

---

## Phase 7: Migration - Markdown to Knowledge Base (From Clarifications)

**Goal**: Provide manual migration command to convert all existing Markdown files to knowledge base entries with backup, verification, and rollback capability

**Independent Test**: Run migration command, verify all Markdown files converted to knowledge entries in PostgreSQL, verify backup created, run verification mode, test rollback restores original state

### Tests for Migration (TDD - Write FIRST, ensure FAIL before implementation)

- [x] T085 [P] Write failing integration test for MarkdownMigrationAdapter.migrate_all_agents in tests/integration/knowledge/test_markdown_migration.py
- [x] T086 [P] Write failing integration test for backup creation (FR-017) in tests/integration/knowledge/test_markdown_migration.py
- [x] T087 [P] Write failing integration test for rollback capability (FR-018) in tests/integration/knowledge/test_markdown_migration.py
- [x] T088 [P] Write failing integration test for verification mode (FR-019) in tests/integration/knowledge/test_markdown_migration.py

### Implementation for Migration

**Infrastructure Layer**:

- [x] T089 Implement MarkdownMigrationAdapter.migrate_all_agents in contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py (FR-016)
- [x] T090 Implement backup creation with timestamped backup directory in contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py (FR-017)
- [x] T091 Implement rollback capability to restore Markdown-based operation in contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py (FR-018)
- [x] T092 Implement verification mode for comparing Markdown vs migrated knowledge base in contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py (FR-019)

**Application Layer**:

- [x] T093 Implement MigrateMarkdownFilesUseCase in contexts/knowledge/application/use_cases/migrate_markdown_files.py

**API Layer**:

- [x] T094 Implement POST /api/v1/knowledge/migrate endpoint in backend/api/routes/knowledge.py (FR-016)
- [x] T095 Implement POST /api/v1/knowledge/rollback endpoint in backend/api/routes/knowledge.py (FR-018)

**Observability**:

- [x] T096 [P] Instrument Prometheus metric (migration_entries_processed_total) in contexts/knowledge/infrastructure/adapters/markdown_migration_adapter.py

**Checkpoint**: Game Masters can manually trigger migration from Markdown files to knowledge base with automatic backup, verification mode, and rollback capability (SC-007)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [x] T097 [P] Add comprehensive error handling with user-friendly error messages across all API endpoints in backend/api/routes/knowledge.py
- [x] T098 [P] Add input validation and sanitization to prevent injection attacks (FR-015) in backend/api/routes/knowledge.py
- [x] T099 [P] Performance optimization: verify knowledge retrieval <500ms for ≤100 entries (SC-002)
- [x] T100 [P] Performance optimization: verify Admin operations <30s (SC-001)
- [x] T101 [P] Verify 99.9% availability for knowledge retrieval operations (SC-006)
- [x] T102 [P] Verify support for ≥10,000 knowledge entries without performance degradation (SC-008)
- [x] T103 [P] Documentation: Update architecture diagrams in docs/architecture/ with Knowledge Management bounded context
- [x] T104 [P] Documentation: Document knowledge base usage in docs/user-guides/
- [x] T105 [P] Security hardening: Review and test authentication/authorization for all endpoints
- [x] T106 Run full test suite and verify coverage targets (Domain ≥80%, Application ≥70%, Infrastructure ≥60%)
- [x] T107 Run quickstart.md validation end-to-end
- [x] T108 Measure and validate all 8 Success Criteria (SC-001 to SC-008) from spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP foundation for knowledge CRUD
- **User Story 2 (Phase 4)**: Depends on Foundational and US1 domain models - Can start after US1 domain layer complete
- **User Story 3 (Phase 5)**: Depends on Foundational and US1/US2 - Requires knowledge retrieval with access control
- **User Story 4 (Phase 6)**: Post-MVP, can be deferred - Depends on US3 completion
- **Migration (Phase 7)**: Depends on US1 (CRUD operations) - Can be implemented in parallel with US2/US3/US4
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundation for all other stories - Provides core CRUD operations
- **User Story 2 (P2)**: Builds on US1 domain models - Adds access control layer
- **User Story 3 (P1)**: Builds on US1 + US2 - Integrates retrieval with SubjectiveBriefPhase
- **User Story 4 (P3)**: Enhances US3 - Optional semantic retrieval (post-MVP)

### Within Each User Story

- TDD: Tests MUST be written and FAIL before implementation
- Domain models before application use cases
- Application use cases before infrastructure adapters
- Infrastructure adapters before API endpoints
- API endpoints before frontend components
- Observability throughout all layers

### Parallel Opportunities

**Phase 1 (Setup)**: T002, T003, T004 can run in parallel

**Phase 2 (Foundational)**: T007, T008, T009, T010, T011, T012 can run in parallel after T005, T006 complete

**User Story 1 Tests**: T013-T024 can all run in parallel (12 tests)

**User Story 1 Domain Layer**: T025, T026, T027, T029, T030, T031 can run in parallel

**User Story 1 Application Layer**: T032, T033, T034, T035 can run in parallel after domain layer

**User Story 1 Frontend**: T044, T045, T046 can run in parallel

**User Story 1 Observability**: T048, T049, T050 can run in parallel

**User Story 2 Tests**: T051-T055 can run in parallel

**User Story 3 Tests**: T065-T068 can run in parallel

**Migration Tests**: T085-T088 can run in parallel

**Polish Phase**: T097-T105 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD - ensure all FAIL first):
T013: "Write failing unit test for KnowledgeEntry.update_content"
T014: "Write failing unit test for KnowledgeEntry content validation"
T015: "Write failing unit test for AccessControlRule invariants"
T016: "Write failing unit test for CreateKnowledgeEntryUseCase"
T017: "Write failing unit test for UpdateKnowledgeEntryUseCase"
T018: "Write failing unit test for DeleteKnowledgeEntryUseCase"
T019: "Write failing integration test for PostgreSQLKnowledgeRepository.save"
T020: "Write failing integration test for PostgreSQLKnowledgeRepository.get_by_id"
T021: "Write failing integration test for PostgreSQLKnowledgeRepository.delete"
T022: "Write failing contract test for POST /api/v1/knowledge/entries"
T023: "Write failing contract test for PUT /api/v1/knowledge/entries/{id}"
T024: "Write failing contract test for DELETE /api/v1/knowledge/entries/{id}"

# Launch all domain models for User Story 1 together:
T025: "Implement KnowledgeType enum"
T026: "Implement AccessLevel enum"
T027: "Implement AccessControlRule value object"
T029: "Implement KnowledgeEntryCreated domain event"
T030: "Implement KnowledgeEntryUpdated domain event"
T031: "Implement KnowledgeEntryDeleted domain event"

# Launch all application use cases for User Story 1 together:
T032: "Define IKnowledgeRepository port"
T033: "Implement CreateKnowledgeEntryUseCase"
T034: "Implement UpdateKnowledgeEntryUseCase"
T035: "Implement DeleteKnowledgeEntryUseCase"

# Launch all frontend components for User Story 1 together:
T044: "Create KnowledgeAPI service"
T045: "Create KnowledgeEntryForm component"
T046: "Create KnowledgeEntryList component"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 3 Only - Core Functionality)

1. **Phase 1**: Setup (T001-T004)
2. **Phase 2**: Foundational (T005-T012) - **CRITICAL GATE**
3. **Phase 3**: User Story 1 - CRUD operations (T013-T050)
4. **Phase 5**: User Story 3 - SubjectiveBriefPhase integration (T065-T077)
5. **STOP and VALIDATE**: Test US1 + US3 independently
6. **Result**: Game Masters can manage knowledge via Web UI, agents automatically retrieve knowledge during turns

### Incremental Delivery

1. **Foundation**: Setup + Foundational → Database ready, Kafka ready, auth ready
2. **MVP**: US1 + US3 → Knowledge CRUD + Agent retrieval → **DEPLOY/DEMO**
3. **Enhancement 1**: US2 → Access control → **DEPLOY/DEMO**
4. **Enhancement 2**: Migration (Phase 7) → Markdown migration → **DEPLOY/DEMO**
5. **Enhancement 3**: US4 → Semantic retrieval (optional) → **DEPLOY/DEMO**
6. Each increment adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers (after Foundational phase complete):

1. **Developer A**: User Story 1 (T013-T050) - CRUD operations
2. **Developer B**: User Story 2 (T051-T064) - Access control
3. **Developer C**: User Story 3 (T065-T077) - SubjectiveBriefPhase integration
4. **Developer D**: Migration (T085-T096) - Markdown migration
5. Stories complete and integrate independently

---

## Notes

- **Total Tasks**: 108 tasks
- **User Story 1**: 38 tasks (12 tests + 26 implementation)
- **User Story 2**: 14 tasks (5 tests + 9 implementation)
- **User Story 3**: 13 tasks (4 tests + 9 implementation)
- **User Story 4**: 7 tasks (2 tests + 5 implementation) - Post-MVP
- **Migration**: 12 tasks (4 tests + 8 implementation)
- **Parallel Opportunities**: 67 tasks marked [P] can run in parallel
- **TDD Compliance**: 27 test tasks written FIRST per Article III
- **Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1) + Phase 5 (US3) = 75 tasks
- **Format Validation**: ✅ All tasks follow checklist format (checkbox, ID, labels, file paths)
