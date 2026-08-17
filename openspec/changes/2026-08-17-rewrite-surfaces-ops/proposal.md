# Rewrite slice 4 — surfaces, sessions & operations

## Why

The TypeScript greenfield rewrite (ADR-0001/0002) is chartered, and the
adjudicated decisions (wayfinder map #242, tickets #245–#252) are being
backfilled into the `novel-engine` capability as the rewrite's acceptance
contract. Slices 1–3 covered the contract foundation, the authoring core and
data model, and the workflows. This final slice covers everything around the
writing surface: authentication hardening, the session lifecycle, operational
guards, the configuration surface, principal isolation, the CLI, and the
frontend behavior contracts the adjudication kept.

The audit found these behaviors living solely in code (audit §4.1, §4.7,
§4.8–§4.9): constant-time login, lazy session expiry, the setup origin check,
authentication rate limiting, production configuration guards, the CORS
contract, the environment prefix family, principal scoping, and the CLI's
backup-before-migrate semantics. A rewrite that loses any of them would
regress security or operability silently.

## What Changes

- Adds the authentication Requirements: constant-time login, the owner setup
  policy with duplicate and concurrent-setup guards, lazy session expiry,
  logout semantics, and setup same-origin validation (A1–A3, A6–A8).
- Adds the operations Requirements: per-IP token-bucket rate limiting on
  setup/login/guest with proxy trust-chain resolution, production
  configuration guards (non-default secret, forced SQLite, CORS wildcard ban;
  deliberate logout-on-restart outside production), the CORS origin contract,
  and the environment configuration surface (`.env.local`, single prefix
  family, `SECURITY_CORS_ORIGINS` as the one CORS name, defaults) (A9–A11,
  H1–H4).
- Adds the isolation and CLI Requirements: principal-scoped data access with
  the 24-hour guest sandbox cleanup, and the `serve`/`import`/`backup`/
  `doctor` CLI surface (I3, I4).
- Adds the frontend behavior contracts the adjudication kept that
  `novel-studio` does not already express: the three-branch entry flow,
  terminal-state job lists without polling (with the coupling clause to the
  synchronous execution model), in-memory drafts with the explicit bounded
  loss window, the 300-second API client timeout, section-to-kind filtering,
  generated document naming, client-derived export downloads, and the silent
  project entry fallback (G2, G3, G6–G8, G10–G12).
- Declares non-goals: the six pure-frontend Requirements that `novel-studio`
  already expresses well — Editor-first responsive and touch layout,
  APG-compliant Inspector tabs, Explicit asynchronous operation state,
  Recoverable document save conflicts, Route-driven project surfaces, and the
  complete single-author Studio surface list — are NOT re-drafted here. The
  cutover consolidation change carries them into `novel-engine` verbatim.

## Impact

- Extends the `novel-engine` capability; `novel-studio` stays untouched until
  cutover, whose consolidation merges the six carried Requirements verbatim
  and replaces its guest-isolation entry with this slice's principal-scoping
  Requirement.
- Rate-limit and guard failures surface under the slice-1 unified error
  envelope; no new error shapes are introduced.
- The frontend tree is carried forward (ADR-0002): its contract items here are
  retention requirements, verified by browser workflow tests, not rebuilds.
- The job-list and timeout Requirements are coupled to the synchronous
  execution model adjudicated in slice 3; if that model is reopened, both
  MUST be reopened with it.
