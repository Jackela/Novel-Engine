# ARC-001: Domain Refactor Blueprint

- **Status**: Draft
- **Date**: 2025-10-29
- **Authors**: Platform Architecture Guild
- **Related Artifacts**: `specs/001-best-practice-refactor/data-model.md`, `docs/architecture/ports-adapters.md`, `docs/governance/security-controls.md`

## Context

The Novel Engine platform is aligning with Constitution v1.0.1. Existing
documentation and code do not clearly delineate bounded contexts, aggregates,
and anti-corruption layers. This ambiguity increases risk for regressions and
blocks adoption of contract-first workflows and operability standards.

## Decision

1. Adopt four bounded contexts with explicit aggregates and owners:
   - **Simulation Orchestration** – `Campaign` aggregate, turn processing.
   - **Persona Intelligence** – `Persona Machine Spirit` aggregate, Gemini ACL.
   - **Narrative Delivery** – `Narrative Chronicle` aggregate, publishing flow.
   - **Platform Operations** – `Platform Control Plane` aggregate, feature flags and SLO registry.
2. Implement hexagonal ports/adapters for each context and catalog them in
   `docs/architecture/ports-adapters.md`.
3. Maintain a shared anti-corruption layer for external Gemini API that
   enforces retries, caching, and tenant isolation.
4. Reference this ADR from templates and runbooks to ensure all downstream work
   follows the same vocabulary.

## Consequences

- Provides a single source of truth for domain boundaries and anti-corruption
  policies.
- Enables contract-first workflows and observability planning per context.
- Introduces documentation upkeep requirement; future changes must update this
  ADR and associated charters.

## Open Questions

- Event sourcing cadence per aggregate (snapshots, retention) to be defined
  during implementation.
- Potential split of Platform Operations into multiple contexts if responsibilities
  grow (evaluate after backlog review).

## Validation Checklist (2025-10-29)

- [X] Bounded contexts documented in `docs/architecture/bounded-contexts.md`.
- [X] Ports and adapters catalog drafted in `docs/architecture/ports-adapters.md`.
- [X] Gemini ACL responsibilities aligned with `docs/architecture/acls/gemini.md`.
