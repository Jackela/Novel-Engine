# Validation evidence

## Fixed points

- Comparison SHA: `e1e6bb616acc589a58b6242dd0c81635a775c55f`
- Change proposal SHA: `6c20ef86`
- Final local candidate SHA: `4fa7904830a324626fdf4b5eb715958a843f9c07`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0, Vitest 4.1.11

## Implementation and review evidence

`readProposalContext` captures the scoped target/current revision, all current
document revisions, canonical composite document order, and ordered volumes in
one short SQLite read transaction. A deterministic two-connection WAL test
commits state B after state A establishes its snapshot and proves the first
capture is wholly A while the next is wholly B. Prompt assembly then derives
resident context, outline/beat, Lore, metadata, and manuscript exclusively from
that immutable capture before Provider construction or SSE hijack.

Retry tests pin inherited base A. An unchanged target uses A in task, request,
result, and usage evidence. An advanced target B lands one closed failed retry
before prompt/Provider work; same-key outer replay and the post-lookup
`created:false` claim-race branch create no repeated capture or evidence, while
a different key and retry-of-retry remain anchored to A. A missing current
revision retains its pre-existing explicit failure without invented A/B facts.

Independent review first found that resident assembly reapplied an incomplete
sort, legacy public helpers still offered the old scattered-read path, several
retry branches lacked direct evidence, and two OpenWiki pages described the
retired architecture. Repairs made captured canonical order the only authority,
removed the unused helpers, added retry fake-store/claim-race/no-current tests,
and updated the architecture pages. Final specification review reported no
P0-P2 findings; final standards review's sole documentation P2 was then closed.

## Local fixed-SHA evidence

All successful commands below ran from the clean tracked tree at
`4fa7904830a324626fdf4b5eb715958a843f9c07`.

| Validation surface | Result |
|---|---|
| Focused context/prompt/retry/Lore tests | Passed: 11 files and 65 tests before final review repairs; repair-specific tests and the full suite cover the final candidate. |
| Full server tests | Passed serially: 188 files and 1,213 tests in 297.00 seconds. |
| Server gates | Passed: SSOT, hygiene, 560-file size budget, migration channel, 19 llms-txt targets, and OpenAPI snapshot. |
| Server type/lint/architecture/build | Passed: Biome checked 407 files; dependency-cruiser checked 214 modules and 887 dependencies with zero violations; production TypeScript build passed. |
| Full frontend tests | Passed: 67 files and 371 tests in 29.68 seconds. |
| Frontend lint/format/type/build | Passed: 1,913 modules; Novel Engine 0.6.0 identity verified in HTML and 7 JavaScript bundles. |
| API-types drift | Passed; generated types match the OpenAPI snapshot. |
| React Doctor | Passed: score 100 and zero diagnostics. |
| TypeScript-backend Playwright | Passed: 8 of 8 in 23.1 seconds. |
| Strict OpenSpec | Passed: 17 of 17 active changes/specification items. |

The first full server attempt ran concurrently with the full frontend and
static/build suites. Under that combined load,
`auth_rate_limit.test.ts`'s preflight case exceeded its 10-second test timeout;
the run ended at 1,212 passed and 1 timed out. The unchanged file then passed
7 of 7 in an isolated reproduction, and the complete server suite passed all
1,213 tests when rerun alone. No timeout was raised and no product or test code
was changed in response; the failed parallel attempt remains part of the audit
trail and is not counted as a pass.

## Named later changes

Project-detail decomposition, revision-history pagination, review summary/detail
pagination, and project/export catalog pagination remain separate resource
changes. This change also does not turn a cursor or Job replay key into a
database snapshot; it owns only one proposal-context capture and explicit retry
base semantics.

## External and release gates

This change remains active and unarchived. Required GitHub checks were not run
because no push or pull request was authorized. Production dependency audit,
Linux execution, and container persistence/restart therefore remain `not run`;
owner is the repository maintainer and closure requires all live required
contexts to pass on the exact integration SHA. No separate visual acceptance is
required because production UI and copy did not change. Release authorization
remains owner-required and is not implied by local or agent evidence.
