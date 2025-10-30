# Constitution Gate Workbook

## Overview

This workbook captures mandatory verification steps derived from the Novel
Engine Constitution v1.0.1. Use it during `/speckit.plan`, `/speckit.tasks`,
and code reviews to document gate status.

## Gate Checklist

- [ ] **Domain-Driven Narrative Core** — Reference ADR ARC-001; confirm bounded contexts/ports updated in `docs/architecture/bounded-contexts.md` and `ports-adapters.md`.
- [ ] **Contract-First Experience APIs** — OpenAPI/GraphQL artifacts updated with versioning, idempotency, and rate-limit notes; lint and pact results attached.
- [ ] **Data Stewardship & Persistence** — Data protection charter reviewed, tenancy safeguards documented, and rollback/RPO plans captured.
- [ ] **Quality Engineering & Testing Discipline** — pytest, Pact, Playwright, k6, and mutation suites planned or completed; failures triaged with owners.
- [ ] **Operability, Security & Reliability** — Observability dashboards, feature flag strategy, and runbook/tabletop updates validated.
- [ ] **Documentation & Knowledge Stewardship** — README, onboarding guides, quickstarts, and this workbook entry refreshed with links to supporting docs.

## Run Log

| Date | Feature | Gate Summary | Notes |
|------|---------|--------------|-------|
| 2025-10-29 | 001-best-practice-refactor | Pending | Initial workbook created; populate once plan/tasks executed. |
| 2025-10-29 | 001-best-practice-refactor | PASS (plan/tasks review) | Gates validated via documentation audit and contract lint run. |
