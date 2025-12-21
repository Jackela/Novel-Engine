---

description: "Task list for Project Best-Practice Refactor"
---

# Tasks: Project Best-Practice Refactor

**Input**: Design documents from `/specs/001-best-practice-refactor/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are optional; include only when they add coverage for governance-critical paths. Contract linting and dashboard verification are required due to constitution gates.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- Prefix descriptions with bounded context or adapter being updated when relevant

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare shared tooling, governance references, and environment baselines before story work begins.

- [X] T001 [Tooling] Update dependency locks in requirements.txt, requirements-test.txt, and frontend/package.json
- [X] T002 [Governance] Verify references in .specify/memory/constitution.md and AGENTS.md#codex
- [X] T003 [P] [Architecture] Generate ADR scaffold at docs/adr/ARC-001-domain-refactor.md
- [X] T004 [Automation] Configure contract linting entrypoint at scripts/contracts/run-tests.sh

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish mandatory documentation structure, metrics baseline, and QA checks required by all user stories.

- [X] T005 [Architecture] Create bounded context glossary in docs/architecture/bounded-contexts.md
- [X] T006 [Observability] Capture baseline metrics snapshot in reports/observability/baseline.md
- [X] T007 [P] [Quality Engineering] Record regression benchmark results in reports/qa/regression-2025-10-29.md (pytest, Playwright, k6)
- [X] T008 [P] [Governance] Assemble constitution gate workbook in docs/governance/constitution-checks.md
- [X] T009 [Architecture] Add ARC-001 entry to docs/adr/index.md

---

## Phase 3: User Story 1 - Architect Maps Domain Boundaries (Priority: P1) 🎯 MVP

**Goal**: Deliver the canonical bounded-context and aggregate blueprint with ports/adapters documented.

**Independent Test**: Review ARC-001 ADR bundle, data-model.md cross-check, and constitution gate compliance metrics without code changes.

### Tests for User Story 1 (documentation validation)

- [X] T010 [P] [US1] [Architecture] Complete blueprint validation checklist in docs/adr/ARC-001-domain-refactor.md

### Implementation for User Story 1

- [X] T011 [US1] [Simulation Orchestration] Finalize aggregate invariants in specs/001-best-practice-refactor/data-model.md
- [X] T012 [P] [US1] [Architecture] Map module ownership by context in docs/architecture/context-mapping.md
- [X] T013 [US1] [Architecture] Capture port/adapter matrix in docs/architecture/ports-adapters.md
- [X] T014 [US1] [Persona Intelligence] Document Gemini anti-corruption layer (cache TTLs, retries, tenant isolation, fallback path) in docs/architecture/acls/gemini.md
- [X] T015 [US1] [Documentation] Refresh architecture overview links in README.md

**Checkpoint**: All contexts, aggregates, and adapters cataloged with owners and invariants.

---

## Phase 4: User Story 2 - Delivery Lead Aligns Contracts & Workflows (Priority: P2)

**Goal**: Align external contracts and workflow gates with constitution-driven practices.

**Independent Test**: Contract lint passes, governance checklists updated, and stakeholders confirm rate-limit/idempotency documentation.

### Tests for User Story 2

- [X] T016 [P] [US2] [Contract Testing] Run contract linting against specs/001-best-practice-refactor/contracts/openapi-refactor.yaml
- [X] T017 [P] [US2] [Governance] Execute dry-run using docs/governance/constitution-checks.md with .specify/templates artifacts

### Implementation for User Story 2

- [X] T018 [US2] [Experience API] Apply contract annotations in apps/api/http/world_router.py and api_server.py
- [X] T019 [US2] [Governance] Update plan and spec templates in .specify/templates/plan-template.md and .specify/templates/spec-template.md
- [X] T020 [US2] [Platform Operations] Publish rate-limit and idempotency policies in docs/governance/api-policies.md
- [X] T021 [US2] [Security] Document RBAC/ABAC matrix and token validation flow in docs/governance/security-controls.md
- [X] T022 [US2] [Data Protection] Record data protection and audit commitments in docs/governance/data-protection.md
- [X] T023 [US2] [Quality Engineering] Extend contract validation playbook in docs/qa/contract-validation.md
- [X] T024 [US2] [Automation] Align CI contract runner at scripts/contracts/run-tests.sh with lint workflow

**Checkpoint**: Contracts reflect constitution mandates; governance templates enforce new gates.

---

## Phase 5: User Story 3 - Reliability Captain Drives Operational Excellence (Priority: P3)

**Goal**: Deliver observability charter, feature flag rollout plan, and incident response readiness aligned to refactored architecture.

**Independent Test**: Tabletop runbook exercise (documented) confirms observability metrics, feature flag strategy, and rollback steps exist.

### Tests for User Story 3

- [X] T025 [P] [US3] [Operations] Record tabletop validation results in docs/runbooks/tabletop-2025-10-29.md

### Implementation for User Story 3

- [X] T026 [US3] [Observability] Draft charter in docs/observability/charter.md
- [X] T027 [US3] [Release Engineering] Update feature flag rollout manual in docs/release/feature-flags.md
- [X] T028 [US3] [Resiliency] Document controls in docs/architecture/resiliency.md
- [X] T029 [US3] [Incident Response] Refresh runbook in docs/runbooks/incident-response.md
- [X] T030 [US3] [Observability] Catalog telemetry field standards in docs/observability/logging-telemetry.md

**Checkpoint**: Operational documents ready for production deployment and monitoring.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Consolidate documentation, communication, and final governance alignment across stories.

- [X] T031 [P] [Communications] Publish refactor briefing in docs/comms/refactor-briefing.md
- [X] T032 [Training] Harmonize onboarding guide in docs/onboarding/guide.md with new workflows
- [X] T033 [Governance] Update changelog references in CHANGELOG.md
- [X] T034 [P] [Quality Assurance] Perform final documentation QA against success criteria (SC-001..SC-005) in specs/001-best-practice-refactor/spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup → Foundational → US1 → US2 → US3 → Polish
- User Story phases are sequential by priority; US2 depends on completion of US1, US3 depends on US2

### User Story Dependencies

- US1 establishes canonical blueprint and must be complete before contract or operations alignment
- US2 builds on US1 outputs to adjust contracts and workflows
- US3 depends on updated workflows to define observability and rollout processes

### Within Each User Story

- Documentation validation tasks may run in parallel with content updates where labeled [P]
- Ensure tests (linting, dry-runs, tabletop) execute after documentation tasks complete

### Parallel Opportunities

- Setup tasks T001–T004 can run concurrently where marked [P]
- Foundational metrics baseline (T007) can run in parallel with governance workbook (T008)
- In US1, context mapping (T012) can proceed alongside blueprint validation (T010)
- In US2, contract linting (T016), governance dry-run (T017), and security/data protection documentation (T021–T022) can execute independently once prerequisites land
- Polish phase tasks T031 and T034 can run parallel to communication updates

---

## Implementation Strategy

1. **MVP (US1)**: Deliver bounded context blueprint, ports/adapters, and ADR references—enables downstream teams to understand refactor scope. 
2. **Extend Contracts & Workflows (US2)**: Update API contracts, governance templates, and security/data-protection controls to enforce new gates. 
3. **Operational Hardening (US3)**: Finalize observability, feature flags, and incident response to ensure production readiness. 
4. **Polish**: Communicate changes, refresh onboarding, and confirm success criteria.
