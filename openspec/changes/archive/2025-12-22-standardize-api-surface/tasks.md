# Tasks: Standardize API Surface

## 1. Audit and classify routes
- [x] Inventory all FastAPI route prefixes and list “product API” vs “tooling/observability API”.
- [x] Find and document all `/api/v1` references in code/docs; label each as “must migrate” (product API) or “out of scope” (non-product). See `openspec/changes/standardize-api-surface/audit.md`.

## 2. Standardize the product API policy
- [x] Ensure product endpoints exist under `/api/*` (canonical).
- [x] Ensure product endpoints are NOT served under `/api/v1/*`.
- [x] Ensure any route discovery/endpoints map only lists real routes and uses `/api/*` (no stale `/api/v1/*` references).

## 3. Update docs and examples
- [x] Update docs under `docs/api/` and examples under `examples/` to match the policy (use `/api/*` only).
- [x] Update security config allowlists/deny rules referencing old paths.

## 4. Tests and validation
- [x] Add/extend contract tests ensuring product endpoints are available under `/api/*` and not under `/api/v1/*`.
- [x] Run full CI validation suite and `openspec validate standardize-api-surface --strict`.
