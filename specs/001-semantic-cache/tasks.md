# Tasks: Semantic Cache

**Input**: Design documents from `/specs/001-semantic-cache/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL. This plan focuses on implementation checklists; add tests if requested.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize folders and configuration toggles per plan

- [X] T001 Create cache SDK directories in src/caching/ (interfaces, providers, indexes, events)
- [X] T002 [P] Add feature toggles (enable_exact_cache, enable_semantic_cache, enable_single_flight) in src/config/caching.py
- [X] T003 [P] Prepare metrics module scaffold in src/metrics/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core SDK constructs and key normalization before any story work

- [X] T004 Implement Cache interfaces in src/caching/interfaces.py
- [X] T005 [P] Implement KeyBuilder with bucketing (temp/top_p/max_tokens) in src/caching/key_builder.py
- [X] T006 [P] Implement ExactCache (LRU+TTL, tags) in src/caching/exact_cache.py
- [X] T007 [P] Refactor semantic cache to pluggable provider/index in src/caching/semantic_cache.py
- [X] T008 Implement in-memory EventBus and InvalidationService in src/caching/events.py
- [X] T009 [P] Implement MetricsPublisher (in-memory) in src/metrics/inmemory.py

**Checkpoint**: Foundation ready – user story implementation can begin

---

## Constitution Alignment Gates (Blocking)

**Purpose**: Mandatory governance tasks per Constitution. All items below MUST complete and pass before user story work proceeds.

- [X] T031 Document bounded context impact and propose ADR updates in docs/architecture/bounded-contexts.md and docs/adr/ARC-SEMANTIC-CACHE.md
- [X] T032 Contract governance: add contract lint job for specs/001-semantic-cache/contracts/cache-api.yaml (CI config) and run local lint
 - [X] T033 Consumer pact checks: scaffold pact tests for internal consumers in tests/contract/ (CI integration)
- [X] T034 Data stewardship: update docs/governance/data-protection.md with cache retention/tags; verify tenancy labels in metrics
- [X] T035 Testing discipline: ensure automated suites (unit/integration/contract) include new coverage; update CI gating in .github/workflows/
- [X] T036 Operability: expose metrics endpoint; update docs/runbooks/cache-observability.md and feature flags in docs/runbooks/feature-flags.md
- [X] T037 Knowledge stewardship: update docs/governance/constitution-checks.md with run date and gate outcomes

## Phase 3: User Story 1 - 快速命中与稳定复用（入口缓存优先） (Priority: P1) 🎯 MVP

**Goal**: Exact→Semantic→Provider拦截链，降低延迟与成本

**Independent Test**: 语义相近请求在不调用提供方时返回一致结果，并附相似度

### Implementation for User Story 1

- [X] T010 [P] [US1] Integrate KeyBuilder into LLM client in src/agents/persona_agent/llm_integration/llm_client.py
- [X] T011 [P] [US1] Add ExactCache lookups and writes (write-on-completion) in src/agents/persona_agent/llm_integration/llm_client.py
- [X] T012 [P] [US1] Add SemanticCache two-threshold policy + guard checks in src/agents/persona_agent/llm_integration/llm_client.py
- [X] T013 [US1] Emit cache hit metadata (type, similarity) via response metadata in src/agents/persona_agent/llm_integration/llm_client.py
- [X] T014 [US1] Wire metrics for hits/misses and saved cost in src/agents/persona_agent/llm_integration/llm_client.py
- [X] T014A [US1] Enforce boundary checks in semantic hits (model_name/template_id+version/index_version/date partition) in src/agents/persona_agent/llm_integration/llm_client.py
 
**Checkpoint**: US1 independently testable（命中率与回退路径验证）

 

---

## Phase 4: User Story 2 - 事件驱动的精确失效（保证新鲜度） (Priority: P1)

**Goal**: Tag精确清除与变更事件联动

**Independent Test**: 模板/索引/角色变更后，仅相关条目被清除，命中新鲜

### Implementation for User Story 2

 - [X] T015 [P] [US2] Attach tags on cache write (character, tmpl, tmplv, idxv, model, locale) in src/caching/exact_cache.py
 - [X] T016 [P] [US2] Map events → tags in InvalidationService in src/caching/invalidation.py
- [X] T017 [US2] Add POST /cache/invalidate handler in api_server.py per specs/001-semantic-cache/contracts/cache-api.yaml
- [X] T018 [US2] Publish events from template/index/model changes in src/agents/persona_agent/core/character_data_manager.py, src/infrastructure/postgresql_manager.py, src/agents/persona_agent/llm_integration/llm_client.py

**Checkpoint**: US2 independently testable（事件触发后命中新鲜）

---

## Phase 5: User Story 3 - 流式回放一致性（SSE/WebSocket） (Priority: P2)

**Goal**: 片段回放与完成写入的一致性

**Independent Test**: 新订阅者可回放历史片段并无缝跟随；完成后写入最终缓存

### Implementation for User Story 3

- [X] T019 [P] [US3] Implement ChunkCache storage (chunks, offsets, complete flag) in src/caching/chunk_cache.py
- [X] T020 [P] [US3] Add SSE/WebSocket replay integration (prefer SSE) in api_server.py
- [X] T021 [US3] Ensure write-on-completion path updates Exact/Semantic caches in src/agents/persona_agent/llm_integration/llm_client.py

**Checkpoint**: US3 independently testable（片段回放与完成落盘）

---

## Phase 6: User Story 4 - 并发风暴保护与复用（Single-Flight） (Priority: P2)

**Goal**: 同键并发合并、去抖与负缓存

**Independent Test**: 高并发相同键仅一次上游调用，其他请求复用结果

### Implementation for User Story 4

- [X] T022 [P] [US4] Add inflight map and single-flight futures in src/bridge/llm_coordinator.py
- [X] T023 [P] [US4] Add debounce window & batch merge in src/bridge/llm_coordinator.py
- [X] T024 [P] [US4] Implement negative cache + backoff per key/provider in src/bridge/llm_coordinator.py
- [X] T025 [US4] Expose GET /cache/metrics based on metrics publisher in api_server.py

---

## Reporting & Contracts Enhancements

**Purpose**: Fulfill budget linkage reporting and contract-first validations prior to runtime usage

- [X] T038 Add monthly savings report generator at scripts/reporting/cache_savings_report.py (reads metrics and outputs CSV/Markdown)
- [X] T039 Extend metrics aggregation to compute saved_tokens and saved_cost in src/metrics/inmemory.py
- [X] T040 Contract lint and update for saved_tokens/saved_cost fields in specs/001-semantic-cache/contracts/cache-api.yaml (CI + local)

---

## Contract Tests (Consumer)

**Purpose**: Minimal scaffolding to satisfy contract-first validation

- [X] T033 Add consumer contract test scaffold for cache endpoints in tests/contract/test_cache_api_contract.py

**Checkpoint**: US4 independently testable（单飞合并率与上游调用次数可测）

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: 统一优化与文档

- [X] T026 [P] Improve metrics snapshot aggregation in src/metrics/inmemory.py
- [X] T027 Documentation updates per quickstart in specs/001-semantic-cache/quickstart.md
- [X] T028 Performance tuning of thresholds and TTL in src/caching/semantic_cache_adapter.py and src/config/caching.py
- [X] T029 Security: skip cache reads/writes when context.sensitive=true (llm_client)
- [X] T030 Run quickstart validation and finalize docs in specs/001-semantic-cache/

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) → Foundational (Phase 2) → Constitution Alignment Gates (Blocking) → US1/US2 (P1) → US3/US4 (P2) → Reporting & Contracts → Polish

### User Story Dependencies

- US1, US2 depend on foundational only; US3 depends on foundational + US1; US4 depends on foundational

### Parallel Opportunities

- Setup T002–T003 can run in parallel
- Foundational T005–T007–T009 can run in parallel
- US1 T010–T012 can run in parallel (different code sections)
- US2 T015–T017 can run in parallel
- US4 T022–T024 can run in parallel

## Implementation Strategy

- MVP = US1 (入口缓存命中与复用)
- Phase rollout: enable semantic cache in canary; monitor metrics; proceed to US2 events; then US3/US4
