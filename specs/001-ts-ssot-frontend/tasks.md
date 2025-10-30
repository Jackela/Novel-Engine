# Tasks: Frontend Type Safety and Styling SSOT

**Input**: Design documents from `/specs/001-ts-ssot-frontend/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Not mandated by spec; include minimal parsing tests for DTOs where specified.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- [P]: Can run in parallel (different files, no dependencies)
- [Story]: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize SSOT scaffolding and scripts

- [X] T001 Create typed tokens file at frontend/src/styles/tokens.ts
- [X] T002 Create MUI theme file derived from tokens at frontend/src/styles/theme.ts
- [X] T003 [P] Add token build script at frontend/scripts/build-tokens.mjs to emit frontend/src/styles/design-system.css
- [X] T004 [P] Wire package scripts in frontend/package.json (add `build:tokens` and include in `build` lifecycle)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Hardening TypeScript and linting gates; stylelint guardrails

- [ ] T005 Update strict flags in frontend/tsconfig.json (isolatedModules, noImplicitReturns, noUncheckedIndexedAccess, exactOptionalPropertyTypes, useUnknownInCatchVariables, noFallthroughCasesInSwitch, noUnusedLocals, verbatimModuleSyntax)
- [ ] T006 Extend TypeScript ESLint coverage in frontend/eslint.config.js for `**/*.{ts,tsx}` with @typescript-eslint rules (no-explicit-any, consistent-type-imports) and react-hooks
- [X] T007 [P] Add Stylelint config at frontend/.stylelintrc.cjs to enforce CSS variables usage and forbid hex in CSS files
- [X] T008 [P] Add stylelint npm script in frontend/package.json (e.g., `lint:styles`)

**React Query foundation**

- [X] T030 Add QueryClientProvider in frontend/src/App.tsx and initialize a shared query client

**Lint enforcement for TSX**

- [ ] T031 [P] Add ESLint rule/config to forbid hex color literals in TSX (styled() and sx) in frontend/eslint.config.js

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Constitution Alignment Gates

- [ ] CG001 Add ADR documenting SSOT and server-state decisions at docs/adr/FE-001-ssot-and-server-state.md (create docs/adr/ if missing)
- [ ] CG002 Ensure contracts reference copy exists at specs/001-ts-ssot-frontend/contracts/openapi.yaml (no backend change)
- [ ] CG003 Document boundary parsing (date normalization) in specs/001-ts-ssot-frontend/data-model.md
- [X] CG004 Ensure CI runs type-check, ESLint (TS), Stylelint, unit tests in .github/workflows/ci.yml (jobs: install deps in frontend; run `npm run type-check`, `npm run lint:all`, `npm test`, `npm run tokens:check`)
- [ ] CG005 Update DESIGN_SYSTEM.md with SSOT guidance at frontend/DESIGN_SYSTEM.md
- [ ] CG006 Update Constitution Workbook entry at docs/governance/constitution-checks.md

---

## Phase 3: User Story 1 - Enforce Strong Type Safety (Priority: P1) 🎯 MVP

**Goal**: Project-wide strict type checking and linting; eliminate `any`; typed DTOs

**Independent Test**: `npm run type-check` and `npm run lint` pass in frontend; introducing implicit `any` fails CI

### Tests for User Story 1 (write first)

- [X] T032 [US1] Add unit tests for DTO transforms at frontend/src/test/dto.transforms.test.ts (valid and malformed payload cases)

### Implementation for User Story 1

- [X] T009 [US1] Define DTO interfaces for API responses at frontend/src/types/dto.ts
- [X] T010 [P] [US1] Refactor transforms to typed DTOs in frontend/src/services/api.ts (remove `any` in response handlers)
- [X] T011 [P] [US1] Convert component to TSX with typed props at frontend/src/components/ApiKeySetup.jsx → frontend/src/components/ApiKeySetup.tsx
- [X] T012 [P] [US1] Convert component to TSX with typed props at frontend/src/components/CharacterSelection.jsx → frontend/src/components/CharacterSelection.tsx
- [X] T013 [P] [US1] Convert component to TSX with typed props at frontend/src/components/OnboardingWizard.jsx → frontend/src/components/OnboardingWizard.tsx
- [X] T014 [US1] Flip `allowJs` to false in frontend/tsconfig.json after converting all remaining .jsx files

### Additional JSX conversions (complete coverage)

- [X] T033 [P] [US1] Convert component to TSX with typed props at frontend/src/components/ErrorDisplay.jsx → frontend/src/components/ErrorDisplay.tsx
- [X] T034 [P] [US1] Convert component to TSX with typed props at frontend/src/components/ProgressTracker.jsx → frontend/src/components/ProgressTracker.tsx
- [X] T035 [P] [US1] Convert component to TSX with typed props at frontend/src/components/SimpleCharacterSelection.jsx → frontend/src/components/SimpleCharacterSelection.tsx
- [X] T036 [P] [US1] Convert component to TSX with typed props at frontend/src/components/TestCharacterSelection.jsx → frontend/src/components/TestCharacterSelection.tsx
- [X] T037 [P] [US1] Convert component to TSX with typed props at frontend/src/components/WizardNavigation.jsx → frontend/src/components/WizardNavigation.tsx
- [X] T038 [P] [US1] Convert component to TSX with typed props at frontend/src/components/WizardStep.jsx → frontend/src/components/WizardStep.tsx
- [X] T039 [P] [US1] Convert entry file to TSX at frontend/src/main.jsx → frontend/src/main.tsx

**Checkpoint**: Type-check and lint pass with strict settings and no `any` in api transforms

---

## Phase 4: User Story 2 - Single Source of Truth for Styling (Priority: P2)

**Goal**: Tokens as SSOT; theme derived from tokens; no hard-coded hex in components

**Independent Test**: Changing a token in tokens.ts updates visuals across refactored components without editing component code

### Tests for User Story 2 (write first)

- [X] T040 [US2] Add token drift and contrast check script at frontend/scripts/check-tokens-contrast.mjs; validate generated CSS vs expected tokens and WCAG contrast

### Implementation for User Story 2

- [X] T015 [US2] Audit and reconcile existing frontend/src/styles/design-system.css with generated output; ensure import order (generated then manual) and add transitional note
- [X] T016 [US2] Refactor to consume imported theme in frontend/src/App.tsx (remove inline createTheme palette)
- [X] T017 [P] [US2] Refactor styled component to theme values in frontend/src/components/layout/GridTile.tsx (replace hex with theme.palette and theme.shadows)
- [X] T018 [P] [US2] Address lint violations by removing remaining hex literals flagged by ESLint in TSX
- [X] T021 [P] [US2] Configure Stylelint to enforce CSS variable usage in CSS only (no TSX) in frontend/.stylelintrc.cjs

**Checkpoint**: No hex literals remain in refactored files; tokens control visuals

---

## Phase 5: User Story 3 - Predictable Server-State Caching (Priority: P3)

**Goal**: Standardized, cache-aware server-state hooks; remove custom API cache/dedup

**Independent Test**: Concurrent duplicate reads dedupe to one network call; cache invalidation refreshes stale data

### Implementation for User Story 3

- [X] T022 [US3] Create typed query hooks at frontend/src/services/queries.ts (useCharactersQuery, useCharacterDetailsQuery, useGenerationStatusQuery, useHealthQuery, useSystemStatusQuery)
- [X] T023 [P] [US3] Refactor consumer to use queries in frontend/src/components/CharacterSelection.tsx (replace direct service calls)
- [X] T024 [P] [US3] Remove APICache and request deduplication from frontend/src/services/api.ts for all read endpoints covered by queries
- [X] T025 [US3] Add parsing unit tests for DTO transforms in frontend/src/test/dto.transforms.test.ts (api.ts transform* functions; include malformed payload cases)
- [X] T026 [US3] Export stable query keys from frontend/src/services/queries.ts and document invalidation patterns in specs/001-ts-ssot-frontend/quickstart.md

**Checkpoint**: Read flows are standardized with typed hooks; no bespoke caching

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, ADRs, CI polish

- [X] T027 Update SSOT documentation at frontend/DESIGN_SYSTEM.md (declare tokens as SSOT; update usage examples)
- [X] T028 Add ADR capturing decisions at docs/adr/FE-001-ssot-and-server-state.md
- [X] T029 [P] Update constitution workbook with references at docs/governance/constitution-checks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies — can start immediately
- Foundational (Phase 2): Depends on Setup completion — BLOCKS all user stories
- User Stories (Phase 3+): All depend on Foundational phase completion
- Polish (Final Phase): Depends on desired user stories completion

### User Story Dependencies

- User Story 1 (P1): Independent after Foundational
- User Story 2 (P2): Independent after Foundational
- User Story 3 (P3): Independent after Foundational

### Parallel Opportunities

- [P] tasks within Setup and Foundational can run concurrently
- Within US1: TSX conversions (T011–T013) and API refactor (T010) can run in parallel
- Within US2: Theme refactor (T019) and styled component refactor (T020) can run in parallel after tokens/theme exist
- Within US3: Consumer refactor (T023) and API cache removal (T024) can proceed in parallel after queries.ts scaffold

---

## Parallel Example: User Story 1

```bash
# Run in parallel
Task: "T011 [US1] Convert ApiKeySetup.jsx → ApiKeySetup.tsx"
Task: "T012 [US1] Convert CharacterSelection.jsx → CharacterSelection.tsx"
Task: "T013 [US1] Convert OnboardingWizard.jsx → OnboardingWizard.tsx"
Task: "T010 [US1] Refactor api.ts transforms to typed DTOs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. STOP and VALIDATE: Type-check + lint pass; conversions complete

### Incremental Delivery

1. Setup + Foundational → baseline gates in place
2. US1 → strict types + DTOs
3. US2 → tokens/theme + refactors
4. US3 → server-state standardization

### Parallel Team Strategy

- After Foundational: split US1/US2/US3 among contributors as listed in Parallel Opportunities
