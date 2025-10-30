# Implementation Plan: Frontend Type Safety and Styling SSOT

**Branch**: `001-ts-ssot-frontend` | **Date**: 2025-10-30 | **Spec**: specs/001-ts-ssot-frontend/spec.md
**Input**: Feature specification from `specs/001-ts-ssot-frontend/spec.md`

## Summary

Strengthen type safety and linting across the frontend, enforce a single source of truth (SSOT) for design tokens, and standardize server-state access. Styling SSOT will be implemented via a build-generated stylesheet emitted from tokens (audited to align with existing design-system.css). All read endpoints will migrate to a standardized, cache-aware access pattern with a shared QueryClientProvider. CI gates block on type-check, lint (TS + hex-ban in TSX), stylelint (CSS), DTO tests, and token drift/contrast checks.

## Technical Context

**Language/Version**: TypeScript 5.x, React 18, Node 18 toolchain  
**Primary Dependencies**: Vite 7, MUI v5, Redux Toolkit, React Query (with QueryClientProvider), Axios, ESLint (+ TS plugin), Stylelint (CSS only)  
**Storage**: N/A (frontend-only; server persistence out of scope)  
**Testing**: Vitest + Testing Library (unit), Playwright (e2e), tsc (type-check)  
**Target Platform**: Modern browsers (Chromium, Firefox, WebKit), desktop and mobile  
**Project Type**: Web application  
**Performance Goals**: Initial route TTI ≤ 3s on mid-tier mobile; maintain 60fps interactions; individual chunks ≤ 800KB (warn) with code-splitting for heavy libs  
**Constraints**: WCAG 2.1 AA contrast; deterministic token propagation via build-generated CSS; hex color literals forbidden in TSX/CSS  
**Scale/Scope**: Frontend-only refactor across existing app; migrate all read endpoints and refactor core layout/components to tokens/theme (no new screens in this feature)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Domain-Driven Narrative Core**: No domain model changes; add ADR documenting styling SSOT and server-state standardization (docs/adr/FE-001-ssot-and-server-state.md). No cross-context coupling.
- **Contract-First Experience APIs**: No backend contract changes; generate client-consumed contract doc under this feature’s `contracts/` for reference. CI contract lint unaffected.
- **Data Stewardship & Persistence Discipline**: No storage changes. Boundary parsing rules documented (date normalization) with tests.
- **Quality Engineering & Testing Discipline**: Enforce CI gates for tsc, ESLint (TS rules incl. hex-ban in TSX), Stylelint (CSS); expand unit tests for DTO parsing; token drift/contrast check script; Playwright unchanged.
- **Operability, Security & Reliability**: Frontend-only; no flags/telemetry changes required.
- **Documentation & Knowledge Stewardship**: Update DESIGN_SYSTEM.md to state tokens as SSOT and add quickstart; update Constitution Workbook after design.
- Constitution Gate Workbook Run Date: 2025-10-30 (link to docs/governance/constitution-checks.md after update)

Post-design re-check: PASS — no constitution violations introduced by Phase 1 artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/001-ts-ssot-frontend/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (/speckit.plan)
├── data-model.md        # Phase 1 output (/speckit.plan)
├── quickstart.md        # Phase 1 output (/speckit.plan)
├── contracts/           # Phase 1 output (/speckit.plan)
└── tasks.md             # Phase 2 output (/speckit.tasks - not created here)
```

### Source Code (repository root)

```text
frontend/
├── src/
│  ├── components/
│  ├── hooks/
│  ├── services/
│  │   ├── api.ts
│  │   └── queries.ts          # NEW: standardized server-state hooks
│  ├── styles/
│  │   ├── design-system.css   # Generated from tokens (build step)
│  │   ├── tokens.ts           # NEW: typed tokens (SSOT)
│  │   └── theme.ts            # NEW: MUI theme derived from tokens
│  ├── types/
│  └── test/
└── vite.config.ts
```

**Structure Decision**: Web application. Introduce `tokens.ts`, `theme.ts`, and `queries.ts` under existing `frontend/src/`; generate `design-system.css` at build time; wrap app with QueryClientProvider.

## Complexity Tracking

No constitution violations anticipated; no complexity justifications required.
