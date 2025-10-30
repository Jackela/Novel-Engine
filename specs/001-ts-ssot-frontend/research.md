# Research & Decisions: Frontend Type Safety and Styling SSOT

## Decisions

- Decision: Build-generated stylesheet from tokens (Styling SSOT)
  - Rationale: Deterministic token propagation, eliminates runtime drift, simplifies audits and CI checks.
  - Alternatives considered: Runtime CSS variables bridge (more dynamic but adds runtime coupling); Hybrid (adds pipeline complexity for limited gain in v1).

- Decision: Standardize all read endpoints on a cache-aware access pattern
  - Rationale: Remove bespoke caching/dedup logic, unify loading/error UI and invalidation semantics.
  - Alternatives considered: Keep APICache (reimplements features, harder to reason about); Partial migration (prolongs mixed patterns).

- Decision: Strict CI gates from day one
  - Rationale: Immediate quality uplift and prevents debt accumulation.
  - Alternatives considered: Warning-only period (risks lingering violations), mixed severities (adds policy overhead without clear benefit in pre-deploy phase).

## Best Practices Snapshot

- TypeScript: enable strict complements (noImplicitReturns, noUncheckedIndexedAccess, exactOptionalPropertyTypes, useUnknownInCatchVariables, noFallthroughCasesInSwitch, isolatedModules, noUnusedLocals, verbatimModuleSyntax).
- ESLint: @typescript-eslint/parser and plugin; enforce no-explicit-any, explicit-function-return-type (warn), consistent-type-imports, no-unused-vars, react-hooks rules.
- Stylelint: standard config + custom rule to forbid hex literals outside generated CSS; enforce use of CSS variables or theme.
- Server-state: co-locate typed query hooks; stable query keys; dedupe and cache TTLs by domain; explicit invalidation on writes.
- Accessibility: enforce color contrast on tokens; provide design-time checks and a CI rule for contrast regressions.

## Open Questions Resolved

- Scale/Scope for v1: Keep NEEDS CLARIFICATION in plan; does not block implementation since architectural changes are internal.

