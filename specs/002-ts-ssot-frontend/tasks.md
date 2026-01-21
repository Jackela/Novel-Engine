# Tasks: Frontend Type Safety and Styling SSOT

## Phase 1: Setup

- [X] T001 Verify feature branch noted in spec header `specs/002-ts-ssot-frontend/spec.md`
 - [X] T002 Verify Node toolchain and install deps in frontend `frontend/package.json`
- [X] T003 Add CI gates to block on type-check, lint, and tokens checks `/.github/workflows/frontend-ci.yml`
- [X] T004 Add contributor docs link from UI design spec to spec directory `docs/specifications/UI_DESIGN_SPEC.md`

## Phase 2: Foundational

- [X] T005 [P] Add central tokens definition and theme composer `frontend/src/styles/tokens.ts`
- [X] T006 [P] Generate CSS variables from tokens via script `frontend/scripts/build-tokens.mjs`
- [X] T007 Wire ThemeProvider and import generated CSS `frontend/src/App.tsx`
- [X] T008 Enforce TS strict flags in compiler options `frontend/tsconfig.json`
- [X] T009 Extend ESLint to cover TS/TSX with TS rules `frontend/eslint.config.js`
- [X] T010 Add stylelint config for CSS variable hygiene `frontend/.stylelintrc.cjs`
- [X] T011 Add tokens drift and contrast check script `frontend/scripts/check-tokens-contrast.mjs`

## Phase 3: User Story 1 – Consistent Visual System (P1)

- [X] T012 [US1] Write test: tokens build and hex-scan enforce no hard-coded hex in in-scope dirs `frontend/scripts/lint-hex-tsx.mjs`
- [X] T013 [US1] Replace inline palette in app entry with theme imports `frontend/src/App.tsx`
- [X] T014 [US1] Refactor GridTile to use theme tokens (remove hex) `frontend/src/components/layout/GridTile.tsx`
 - [X] T015 [P] [US1] Sweep layout components for hex → tokens (batch 1) `frontend/src/components/layout/*`
 - [X] T016 [P] [US1] Sweep navbar and shared UI for hex → tokens (batch 2) `frontend/src/components/Navbar.tsx`
- [X] T017 [US1] Document token update workflow in UI design spec `docs/specifications/UI_DESIGN_SPEC.md`

## Phase 4: User Story 2 – Contributor-Friendly Styling (P2)

- [X] T018 [US2] Write test: generated CSS variables snapshot from tokens `frontend/tests/unit/tokens.generated-css.snapshot.test.ts`
- [X] T019 [US2] Add tokens quickstart with examples `specs/002-ts-ssot-frontend/quickstart.md`
- [X] T020 [US2] Ensure tokens build emits CSS and theme consistently `frontend/scripts/build-tokens.mjs`
- [X] T021 [US2] Add precommit or CI step to fail on deleted/renamed tokens without migration note `frontend/.github/workflows/frontend-ci.yml`
- [X] T022 [US2] Add doc anchors from README to DESIGN_SYSTEM `frontend/DEVELOPMENT.md`

## Phase 5: User Story 3 – Predictable Data and Loading States (P3)

- [X] T023 [US3] Write tests: hooks loading/error/success states with msw `frontend/tests/unit/hooks.queries.test.tsx`
- [X] T024 [US3] Write smoke test: App renders with providers without runtime errors `frontend/tests/unit/app.smoke.test.tsx`
- [X] T025 [US3] Centralize characters query hooks with typed DTOs `frontend/src/services/queries.ts`
- [X] T026 [US3] Migrate CharacterSelection to use shared hooks `frontend/src/components/StoryWorkshop/CharacterSelectionContainer.tsx`
- [X] T027 [US3] Unify loading/error UI primitives and use across primary screens `frontend/src/components/common/AsyncStates.tsx`
 - [X] T028 [US3] Remove bespoke APICache usage in covered reads `frontend/src/services/api.ts`

## Final Phase: Polish & Cross-Cutting

 - [X] T029 [P] Add tests for DTO transforms (good/malformed payloads) `frontend/tests/unit/api.transforms.test.ts`
 - [X] T030 Update ADR documenting SSOT + server-state split `docs/adr/FE-001-ssot-and-server-state.md`
 - [X] T031 Ensure Constitution workbook updated for this feature `docs/governance/constitution-checks.md`

## Dependencies

- User Story order: US1 → US2 → US3
- Foundational must complete before any user story tasks
- Parallel tasks [P] can run concurrently if they touch different files

## Implementation Strategy

- Prioritize MVP by completing US1 first to deliver visible value; then US2 for contributor ergonomics; finally US3 for server-state consistency.

## Traceability

- T030 documents the SSOT styling and server-state split as an ADR, aligning with Constitution Principle VI (Documentation & Knowledge Stewardship).
- T031 updates the Constitution Gate Workbook, aligning with Constitution Principle VI and validating that gates from Principles II (API Discipline) and IV (Quality Engineering & Testing) are reflected in this feature’s plan/spec/tasks.
