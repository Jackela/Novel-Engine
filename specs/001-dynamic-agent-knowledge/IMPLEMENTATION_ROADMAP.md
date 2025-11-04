# Implementation Roadmap: Dynamic Agent Knowledge and Context System

**Feature ID**: 001-dynamic-agent-knowledge  
**Current Progress**: 45/108 tasks (42%) complete  
**Date**: 2025-01-04  
**Status**: User Story 1 MVP Complete (pending auth integration)

---

## Overview

This roadmap outlines the remaining implementation work across 4 user stories and supporting infrastructure.

**Total Remaining**: 63 tasks (58%)

---

## Phase Status Summary

| Phase | Tasks | Status | Priority | Timeline |
|-------|-------|--------|----------|----------|
| Setup (Phase 1) | 4/4 | ✅ Complete | - | Done |
| Foundational (Phase 2) | 7/8 | ⚠️ 87% | P0 | 1 task deferred |
| User Story 1 (Phase 3) | 40/42 | ✅ 95% | P1 | 2 tasks deferred |
| User Story 2 (Phase 4) | 0/14 | ⏳ Pending | P2 | Next priority |
| User Story 3 (Phase 5) | 0/13 | ⏳ Pending | P1 | Co-MVP with US1 |
| User Story 4 (Phase 6) | 0/7 | ⏳ Pending | P3 | Post-MVP |
| Migration (Phase 7) | 0/12 | ⏳ Pending | P2 | Post-MVP |
| Polish (Phase 8) | 0/12 | ⏳ Pending | P2 | Final phase |

---

## Immediate Priorities

### Priority 0: Authentication Integration (2 tasks)

**Goal**: Complete User Story 1 by integrating authentication

**Tasks**:
- [ ] T008: Implement Novel Engine authentication middleware integration in `backend/api/middleware/auth_middleware.py`
- [ ] T043: Add authentication/authorization checks (admin or game_master role) to all Admin API endpoints

**Acceptance Criteria**:
- Only authenticated users with admin or game_master role can access Admin API
- JWT token validation working
- 401 Unauthorized for unauthenticated requests
- 403 Forbidden for unauthorized roles

**Implementation Steps**:
1. Review existing Novel Engine auth system
2. Create auth middleware for FastAPI
3. Add dependency injection for auth checks
4. Update API endpoints with auth dependencies
5. Test with authenticated and unauthenticated requests
6. Update frontend to handle 401/403 responses

**Estimated Time**: 4-6 hours

---

### Priority 1A: User Story 2 - Permission-Controlled Access (14 tasks)

**Goal**: Enable Game Masters to define access rules for knowledge entries

**Tasks Breakdown**:

#### Tests (5 tasks)
- [ ] T051: Write failing unit test for AccessControlRule.permits with public access
- [ ] T052: Write failing unit test for AccessControlRule.permits with role-based access
- [ ] T053: Write failing unit test for AccessControlRule.permits with character-specific access
- [ ] T054: Write failing unit test for KnowledgeEntry.is_accessible_by
- [ ] T055: Write failing integration test for PostgreSQLKnowledgeRepository.retrieve_for_agent

#### Domain Layer (2 tasks)
- [ ] T056: Implement AgentIdentity value object in `contexts/knowledge/domain/models/agent_identity.py`
- [ ] T057: Implement is_accessible_by method on KnowledgeEntry

#### Application Layer (3 tasks)
- [ ] T058: Define IKnowledgeRetriever port in `contexts/knowledge/application/ports/i_knowledge_retriever.py`
- [ ] T059: Define IAccessControlService port
- [ ] T060: Implement AccessControlService domain service

#### Infrastructure Layer (1 task)
- [ ] T061: Implement retrieve_for_agent method in PostgreSQLKnowledgeRepository with access control filtering

#### Frontend Layer (2 tasks)
- [ ] T062: Create AccessControlPanel component
- [ ] T063: Integrate AccessControlPanel into KnowledgeEntryForm

#### Observability (1 task)
- [ ] T064: Instrument Prometheus metric (access_denied_total)

**Acceptance Criteria**:
- Game Masters can set access rules on knowledge entries
- Agents only retrieve knowledge matching their permissions
- Access violations logged for audit
- Frontend shows access control preview

**Estimated Time**: 2-3 days

---

### Priority 1B: User Story 3 - Agent Context Assembly (13 tasks)

**Goal**: Integrate knowledge retrieval into SubjectiveBriefPhase

**Tasks Breakdown**:

#### Tests (4 tasks)
- [ ] T065: Write failing unit test for AgentContext.to_llm_prompt_text
- [ ] T066: Write failing unit test for RetrieveAgentContextUseCase
- [ ] T067: Write failing integration test for SubjectiveBriefPhaseAdapter.assemble_agent_context
- [ ] T068: Write failing integration test verifying NO Markdown file reads during SubjectiveBriefPhase

#### Domain Layer (2 tasks)
- [ ] T069: Implement AgentContext aggregate
- [ ] T070: Implement to_llm_prompt_text method on AgentContext

#### Application Layer (2 tasks)
- [ ] T071: Define IContextAssembler port
- [ ] T072: Implement RetrieveAgentContextUseCase

#### Infrastructure Layer (3 tasks)
- [ ] T073: Implement SubjectiveBriefPhaseAdapter
- [ ] T074: Modify existing SubjectiveBriefPhase to use adapter instead of Markdown file reads
- [ ] T075: Add feature flag to toggle between Markdown and knowledge base

#### Observability (2 tasks)
- [ ] T076: Instrument Prometheus metrics (knowledge_retrieval_duration_seconds, knowledge_retrieval_count_total)
- [ ] T077: Add OpenTelemetry tracing spans for knowledge retrieval

**Acceptance Criteria**:
- Agents automatically retrieve current knowledge from PostgreSQL during simulation turns
- Markdown files no longer read for agent context (FR-006)
- Access control enforced per FR-009
- Feature flag allows gradual rollout

**Estimated Time**: 3-4 days

---

## Secondary Priorities

### Priority 2A: Migration Tool (12 tasks)

**Goal**: Provide manual migration command to convert Markdown files to knowledge base

**Tasks Breakdown**:

#### Tests (4 tasks)
- [ ] T085: Write failing integration test for MarkdownMigrationAdapter.migrate_all_agents
- [ ] T086: Write failing integration test for backup creation (FR-017)
- [ ] T087: Write failing integration test for rollback capability (FR-018)
- [ ] T088: Write failing integration test for verification mode (FR-019)

#### Infrastructure Layer (4 tasks)
- [ ] T089: Implement MarkdownMigrationAdapter.migrate_all_agents
- [ ] T090: Implement backup creation with timestamped backup directory
- [ ] T091: Implement rollback capability to restore Markdown-based operation
- [ ] T092: Implement verification mode for comparing Markdown vs migrated knowledge base

#### Application Layer (1 task)
- [ ] T093: Implement MigrateMarkdownFilesUseCase

#### API Layer (2 tasks)
- [ ] T094: Implement POST /api/v1/knowledge/migrate endpoint
- [ ] T095: Implement POST /api/v1/knowledge/rollback endpoint

#### Observability (1 task)
- [ ] T096: Instrument Prometheus metric (migration_entries_processed_total)

**Acceptance Criteria**:
- Game Masters can manually trigger migration from Markdown files
- Automatic backup created before migration
- Verification mode compares Markdown vs migrated data
- Rollback capability restores original state

**Estimated Time**: 2-3 days

---

### Priority 2B: Polish & Cross-Cutting Concerns (12 tasks)

**Goal**: Production readiness and quality improvements

**Tasks**:
- [ ] T097: Add comprehensive error handling with user-friendly error messages
- [ ] T098: Add input validation and sanitization to prevent injection attacks
- [ ] T099: Performance optimization: verify knowledge retrieval <500ms for ≤100 entries
- [ ] T100: Performance optimization: verify Admin operations <30s
- [ ] T101: Verify 99.9% availability for knowledge retrieval operations
- [ ] T102: Verify support for ≥10,000 knowledge entries without performance degradation
- [ ] T103: Documentation: Update architecture diagrams
- [ ] T104: Documentation: Document knowledge base usage
- [ ] T105: Security hardening: Review and test authentication/authorization
- [ ] T106: Run full test suite and verify coverage targets
- [ ] T107: Run quickstart.md validation end-to-end
- [ ] T108: Measure and validate all 8 Success Criteria

**Acceptance Criteria**:
- All Success Criteria (SC-001 to SC-008) validated
- Coverage targets met (Domain ≥80%, Application ≥70%, Infrastructure ≥60%)
- Security hardening complete
- Documentation complete

**Estimated Time**: 3-4 days

---

### Priority 3: User Story 4 - Semantic Retrieval (7 tasks, Post-MVP)

**Goal**: Enable semantic relevance-based knowledge retrieval

**Tasks Breakdown**:

#### Tests (2 tasks)
- [ ] T078: Write failing integration test for semantic search with vector embeddings
- [ ] T079: Write failing unit test for semantic relevance scoring

#### Infrastructure Layer (3 tasks)
- [ ] T080: Add vector embedding column to knowledge_entries table (PostgreSQL pgvector extension)
- [ ] T081: Implement embedding generation adapter
- [ ] T082: Implement semantic search in PostgreSQLKnowledgeRepository using vector similarity

#### Application Layer (2 tasks)
- [ ] T083: Update RetrieveAgentContextUseCase to support semantic retrieval mode
- [ ] T084: Implement fallback strategy (semantic if available, timestamp ordering if not)

**Acceptance Criteria**:
- Semantic retrieval enhances agent context assembly
- Relevance-based filtering without exact keyword matches
- Graceful fallback to timestamp ordering

**Estimated Time**: 4-5 days (requires ML model integration)

---

## Implementation Strategy

### Recommended Sequence

#### **Week 1: Complete MVP**
1. **Day 1-2**: Authentication Integration (T008, T043)
   - Integrate auth middleware
   - Protect API endpoints
   - Test with authenticated users
   - **Milestone**: User Story 1 100% complete

2. **Day 3-5**: User Story 2 - Permission-Controlled Access (14 tasks)
   - TDD: Write all tests first
   - Implement domain models (AgentIdentity, is_accessible_by)
   - Implement access control filtering
   - Frontend: AccessControlPanel component
   - **Milestone**: Access control fully functional

#### **Week 2: Agent Integration**
1. **Day 6-10**: User Story 3 - Agent Context Assembly (13 tasks)
   - TDD: Write all tests first
   - Implement AgentContext aggregate
   - Implement RetrieveAgentContextUseCase
   - SubjectiveBriefPhase integration
   - Feature flag for gradual rollout
   - **Milestone**: Agents use PostgreSQL instead of Markdown

#### **Week 3: Migration & Polish**
1. **Day 11-13**: Migration Tool (12 tasks)
   - Implement MarkdownMigrationAdapter
   - Backup and rollback capabilities
   - Verification mode
   - Migration API endpoints
   - **Milestone**: Markdown → PostgreSQL migration tool complete

2. **Day 14-15**: Polish & Quality (12 tasks)
   - Error handling improvements
   - Security hardening
   - Performance validation
   - Documentation updates
   - Full test suite validation
   - **Milestone**: Production-ready release

#### **Post-MVP (Optional)**
- **Week 4+**: User Story 4 - Semantic Retrieval (7 tasks)
  - pgvector integration
  - Embedding generation
  - Semantic search implementation
  - **Milestone**: Enhanced semantic knowledge retrieval

---

## Parallel Development Opportunities

### Multi-Developer Strategy

**Developer A (Backend Specialist)**:
- User Story 2: Domain models, use cases, repository methods
- User Story 3: AgentContext, RetrieveAgentContextUseCase
- Migration Tool: MarkdownMigrationAdapter

**Developer B (Frontend Specialist)**:
- User Story 2: AccessControlPanel component
- User Story 3: Agent context viewer (future)
- Polish: UI improvements, error handling

**Developer C (Infrastructure Specialist)**:
- Authentication integration (T008, T043)
- SubjectiveBriefPhase integration (T074)
- Performance optimization (T099-T102)

**Developer D (QA Specialist)**:
- Write all TDD tests (T051-T055, T065-T068, T078-T079, T085-T088)
- E2E test automation
- Performance testing
- Security testing

---

## Risk Assessment

### High Risk Items

1. **SubjectiveBriefPhase Integration** (T074)
   - **Risk**: Breaking existing simulation logic
   - **Mitigation**: Feature flag, comprehensive testing, gradual rollout
   - **Contingency**: Rollback capability, maintain Markdown fallback

2. **Authentication Integration** (T008, T043)
   - **Risk**: Incompatibility with existing auth system
   - **Mitigation**: Review existing system first, modular design
   - **Contingency**: Standalone auth implementation

3. **Migration Tool** (T089-T095)
   - **Risk**: Data loss during migration
   - **Mitigation**: Mandatory backup, verification mode, rollback capability
   - **Contingency**: Manual migration procedure

### Medium Risk Items

1. **Access Control Performance** (T061)
   - **Risk**: Slow filtering for large datasets
   - **Mitigation**: Database indexes, query optimization
   - **Contingency**: Caching layer, pagination

2. **Semantic Search** (T080-T084)
   - **Risk**: ML model integration complexity
   - **Mitigation**: Optional feature, graceful fallback
   - **Contingency**: Defer to post-MVP

---

## Success Metrics

### User Story 1 (Target: 100%)
- ✅ Backend CRUD: Complete
- ✅ Frontend UI: Complete
- ⏳ Authentication: Pending (T008, T043)
- **Current**: 95% → **Target**: 100%

### User Story 2 (Target: 100%)
- ⏳ Access Control: Pending (14 tasks)
- **Current**: 0% → **Target**: 100%

### User Story 3 (Target: 100%)
- ⏳ Agent Integration: Pending (13 tasks)
- **Current**: 0% → **Target**: 100%

### Overall Feature (Target: 80% for MVP)
- **Current**: 42% → **Target**: 80% (excludes US4, some polish)
- **Tasks**: 45/108 → **Target**: ~86/108

---

## Dependencies & Blockers

### Current Blockers
1. **T008 (Auth Middleware)**: Requires understanding of existing Novel Engine auth system
2. **T074 (SubjectiveBriefPhase Integration)**: Requires access to existing SubjectiveBriefPhase code

### External Dependencies
1. **PostgreSQL**: Database must be running and accessible
2. **Kafka**: Event bus must be configured
3. **Authentication System**: Existing Novel Engine auth infrastructure
4. **SubjectiveBriefPhase**: Existing simulation phase code

### Resolution Strategy
1. Review existing auth system documentation
2. Locate SubjectiveBriefPhase implementation
3. Set up local development environment with all dependencies
4. Create integration test environment

---

## Documentation Requirements

### Technical Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Database schema documentation
- [ ] Architecture diagrams (updated)
- [ ] Integration guide for SubjectiveBriefPhase

### User Documentation
- [ ] Game Master user guide
- [ ] Knowledge entry best practices
- [ ] Migration guide (Markdown → PostgreSQL)
- [ ] Troubleshooting guide

### Developer Documentation
- [ ] Code contribution guide
- [ ] Testing guide
- [ ] Deployment guide
- [ ] Monitoring and observability guide

---

## Next Session Checklist

**Before Starting Next Session**:
- [ ] Review existing Novel Engine authentication system
- [ ] Locate SubjectiveBriefPhase implementation files
- [ ] Verify PostgreSQL database is accessible
- [ ] Verify Kafka is configured
- [ ] Review User Story 2 specification
- [ ] Prepare TDD test scaffolds

**First Tasks to Execute**:
1. Grep for authentication middleware patterns in codebase
2. Read existing auth documentation
3. Locate SubjectiveBriefPhase files
4. Create T008 implementation plan
5. Begin TDD tests for User Story 2

---

**Last Updated**: 2025-01-04  
**Next Review**: After authentication integration complete  
**Owner**: Development Team  
**Status**: 🟢 Active Development
