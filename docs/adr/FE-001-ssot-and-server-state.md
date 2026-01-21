# ADR FE-001: Frontend Styling SSOT and Server-State Standardization

- Status: Accepted
- Date: 2025-10-30
- Owners: Frontend Team
- Related: specs/002-ts-ssot-frontend/spec.md, specs/002-ts-ssot-frontend/plan.md

## Context

The frontend exhibited drift between CSS variables and UI theme tokens and inconsistently handled server reads via bespoke cache/dedupe logic. This led to visual inconsistency, harder refactors, and unpredictable loading/error states.

## Decision

- Establish a Single Source of Truth for styling via tokens defined in `src/styles/tokens.ts`.
- Generate CSS variables (`src/styles/design-system.generated.css`) from tokens and align Tailwind theme tokens to the same source.
- Standardize server-state handling for primary reads via query hooks in `src/services/queries.ts`.
- Remove bespoke API cache usage for covered reads; rely on consumer-level caching (TanStack Query).
- Enforce via CI gates: type-check, ESLint (TS), Stylelint (CSS), TSX hex scan, token drift/contrast check, unit tests.

## Rationale

- SSOT eliminates duplication/drift, accelerates design changes, improves accessibility governance.
- Query-based server state yields predictable loading/error behaviors and deduplication.
- CI gates prevent regression and make the architecture testable.

## Alternatives Considered

- Maintain separate CSS/TS token sets: rejected due to drift risk.
- Only use theme (no CSS variables): rejected; global styles still require variables.
- Continue bespoke caching: rejected; reinvents functionality and reduces observability.

## Consequences

- Contributors add/edit tokens in a single place and run `npm run build:tokens`.
- Components consume tokens via theme/tokens; hard-coded hex in TSX is blocked.
- Server reads for primary flows adopt shared hooks with consistent UX.

## Links

- Design System: frontend/DESIGN_SYSTEM.md
- Plan/Spec: specs/002-ts-ssot-frontend/
- CI: .github/workflows/frontend-ci.yml
