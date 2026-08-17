# Rewrite slice 1 — contract foundation

## Why

The TypeScript greenfield rewrite (ADR-0001/0002) is chartered, and the
adjudicated decisions (wayfinder map #242, tickets #245–#254) now need a
home in the capability specification — the rewrite's acceptance contract.
The current `novel-studio` capability covers only the product skeleton: the
audit found ~62 implicit requirements living solely in code. This first
slice fixes the contract foundation everything else references: the error
envelope, the session cookie/CSRF shapes (including the `novel_engine_*`
rename), the session/provider/health/version surfaces, and the request
validation constraints.

This change creates the new `novel-engine` capability alongside
`novel-studio`. The Python implementation remains authoritative until
cutover (ADR-0001), so `novel-studio` stays valid and is retired only by
the cutover change.

## What Changes

- Adds the `novel-engine` capability with the contract-foundation
  Requirements: product/version authority (workspace manifest, `runtime`
  field), the unified error envelope `{"error":{code,message,details}}`
  (409 conflicts carry `details.current_revision_id`), the
  `novel_engine_session`/`novel_engine_csrf` cookie contract with
  attribute and lifetime rules, CSRF double-submit validation, the
  session/provider endpoint set with payload shapes, the health/version
  surface, and request validation constraints.
- Records deliberate non-goals: the API MUST NOT carry over the dead
  surface — manual snapshot endpoints (`GET/POST /projects/{id}/snapshots`),
  `POST /api/imports` (CLI import remains), and the single-document GET
  route. Import preview stays.

## Impact

- New capability `novel-engine`; `novel-studio` untouched until cutover.
- The OpenAPI baseline regenerated at TS-first-green will differ from the
  Python snapshot by exactly these adjudicated deltas (cookieAuth scheme
  name, error envelope, `/version` `runtime` field, absent dead routes) —
  per the acceptance-contract decision (#252).
- Frontend carried forward: cookie-name regex and the error-extraction
  single path are the only contract-mandated frontend edits.
