# Research: Frontend Type Safety and Styling SSOT

## Decision 1: Styling SSOT via Token Generator

- Decision: Generate both CSS variables and the application theme from a single tokens definition.
- Rationale: Ensures one source controls all styling layers, eliminating drift and enabling fast, safe design updates.
- Alternatives Considered:
  - Maintain parallel token sets in CSS and TS: Rejected due to duplication and drift risk.
  - Rely solely on MUI theme without CSS variables: Rejected because global styles and non-React contexts still need variables.
  - Adopt a full design-system framework: Overkill for current scope; adds complexity without proportional benefit.

## Decision 2: Standardize Server-State Patterns

- Decision: Use a consistent query-based pattern (React Query v3) for primary reads to unify loading, error, and caching behavior.
- Rationale: Eliminates custom caching/dedup logic, improves consistency, and clarifies component responsibilities.
- Alternatives Considered:
  - Keep bespoke APICache/request dedupe: Rejected due to maintenance burden and limited observability.
  - Move reads into Redux slices: Rejected; conflates app state with server state and duplicates caching logic.

## Decision 3: CI Gates for Quality Enforcement

- Decision: Block merges on type-check, lint (TS/JS + styles), and token drift/contrast checks.
- Rationale: Prevents regressions and enforces the SSOT and type-safety goals at the boundary.
- Alternatives Considered:
  - Advisory-only lint: Rejected; reduces effectiveness and allows drift to reappear.
  - Post-merge checks: Rejected; too late to prevent regressions.

## Decision 4: TypeScript Hardening

- Decision: Enforce strict compiler flags and remove unsafe any in primary flows.
- Rationale: Catch defects earlier, improve refactor safety, and make UI states more predictable.
- Alternatives Considered:
  - Partial strictness: Rejected; inconsistent guarantees and higher long-term costs.

## Open Questions (Resolved)

- Backward compatibility: Out of scope; project is pre-release per directive.
- Theming mode count (light/dark/system): Default to current project behavior; token system supports future theme additions.
- Scope of initial migration: Focus on shared components and primary flows; deeper legacy sections can follow.

