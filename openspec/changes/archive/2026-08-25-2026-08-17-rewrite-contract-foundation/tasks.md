## 1. Specification

- [x] 1.1 Draft the contract-foundation deltas in the `novel-engine` capability
- [x] 1.2 `pnpm spec:validate` green

## 2. Server implementation (per `/to-tickets` breakdown)

- [x] 2.1 Error-envelope middleware: single shape, 409 conflict details, opaque 500 with error_id
- [x] 2.2 Session cookie set/clear with the `novel_engine_*` names, attributes, and lifetimes
- [x] 2.3 CSRF double-submit hook with constant-time compare and the three exemptions
- [x] 2.4 Setup/session/providers routes with the adjudicated payload shapes
- [x] 2.5 Health/live/ready probes and the version endpoint with the `runtime` field
- [x] 2.6 Request schema constraints via the shared TypeBox schemas

## 3. Frontend alignment

- [x] 3.1 Cookie-name regex switches to `novel_engine_csrf`
- [x] 3.2 Error extraction collapses to the single envelope path

## 4. Verification

- [x] 4.1 Server contract tests: envelope shapes, CSRF rejection, cookie attributes, readiness, validation constraints
- [x] 4.2 OpenAPI baseline regenerated at first green; diff limited to the adjudicated deltas
