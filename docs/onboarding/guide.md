# Onboarding Guide

## 10-Step Quick Start
1. Clone repository and checkout `001-best-practice-refactor` branch.
2. Install Python dependencies: `pip install -r requirements.txt -r requirements-test.txt`.
3. Install frontend tooling: `npm install --prefix frontend`.
4. Review constitution and governance docs (`.specify/memory/constitution.md`, `docs/governance/*`).
5. Read architecture overview (`docs/architecture/bounded-contexts.md`, `context-mapping.md`, `ports-adapters.md`).
6. Explore API contracts in `specs/001-best-practice-refactor/contracts/openapi-refactor.yaml`.
7. Run baseline tests using `pytest`, Playwright smoke, and k6 smoke scripts (see `reports/qa/regression-2025-10-29.md`).
8. Familiarize with observability/operability docs (`docs/observability/charter.md`, `docs/observability/logging-telemetry.md`).
9. Understand feature flag and incident response workflows (`docs/release/feature-flags.md`, `docs/runbooks/incident-response.md`).
10. Update constitution workbook entry after completing initial walkthrough.

## Contacts
- Architecture Guild: arch@novel-engine.example
- Reliability Council: sre@novel-engine.example
- Product Delivery: delivery@novel-engine.example

