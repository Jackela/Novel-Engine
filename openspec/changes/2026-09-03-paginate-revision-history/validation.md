# Validation evidence

## Current closeout pointer — 2026-09-05

The phase records below retain their original SHAs and results. Later evidence
is recorded in [Draft selection closeout](../../../docs/agents/draft-selection-closeout-2026-09-05.md)
on code candidate `b2019baec05485c9ae4aa930cdeb6e8dccba48ee`.

| Open task | Implementation / validation correspondence | Remaining closure condition |
| --- | --- | --- |
| 5.1 | Server revision pagination, cursor, word-count reconciliation and restore suites; frontend `useRevisionCache.*`, `useDocumentDraft.*`, and `StudioHistoryPanel.*`. The new code candidate passed 463 frontend tests and the full 9-flow TS E2E suite, including History pagination/retry. | Keep server phase results at their historical SHAs; use final-candidate CI for server full and cross-surface validation. |
| 5.2 | New-candidate frontend lint/format/type/unit/build, API drift, React diagnostics, repository gates, strict OpenSpec, and complete E2E passed; independent new review is bounded to the Draft repair. | The full independent UX/revision audit matrix is not supplied by a passing test count or this bounded review. |
| 5.3 | Required CI and canonical-spec/archive step. | Remains open. Record exact final PR SHA/check URLs; no archive or integration in this closeout. |

No historical run is relabeled as a new-SHA run. Human acceptance remains
`not run`; use [the acceptance packet](../../../docs/agents/refactor-human-acceptance-2026-09-05.md).

## Fixed points

- Comparison SHA: `c474c6e3039590067795d4980300a640b873d905`
- Persisted-count implementation SHA: `ea5fb6810eae32da30c24e538bda8c9fb5ab10ac`
- Server pagination implementation SHA: `71a9aad3c12cd4eef3a91b14b66d5f4c3f7f25b3`
- Server review-repair SHA: `c69e56589b93fed95645407d2bf94d53335303d2`
- Frontend pagination implementation SHA: `7f817821c4752a089345238a39ef914ee6456e4c`
- Frontend concurrency repair SHA: `ae4fd1fe7224dc496cc98efdef225e62b22a414b`
- Frontend error-ownership repair SHA: `e221ea4fe7555ba90598b13f96d18138156cb963`
- Final local candidate SHA: pending integrated browser and full-suite validation.
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Persisted revision word-count evidence

The migration was generated with
`pnpm --dir server db:generate --name persist-revision-word-count`. Its SQL adds
only the nullable upgrade-sentinel column; the generated snapshot and journal
were reviewed without manual edits. The migration-channel gate passed.

The exact prior Unicode counter now has one domain implementation. Focused
coverage pins ASCII, Chinese, punctuation, apostrophe, hyphen, numeric, empty,
and unpaired-surrogate behavior. Full Document and Revision projections consume
the stored value and reject null, negative, fractional, `NaN`, and unsafe
integers with the internal `RevisionWordCountInvariantError`.

The sole product revision insertion helper writes the count in the same
transaction for seeds, imports, saves, proposal acceptance, and restores. The
upgrade reconciler reads only `id` and body in stable batches of at most 256,
commits each batch atomically, resumes null rows after interruption, and runs
before export reconciliation and running-job recovery. Tests prove a 257-row
partial resume, 513-row checkpoints `[256, 512, 513]`, preservation of historic
revision fields, and fail-fast startup ordering.

| Validation surface | Result |
|---|---|
| Word-count and reconciliation tests | Passed: 2 files and 16 tests. |
| Seed/import/save/proposal/restore regressions | Passed: 7 files and 41 tests during implementation; independent review reran 29 API-path tests. |
| Server type-check, lint, architecture, size, gates, and build | Passed; architecture checked 216 modules / 895 dependencies and size checked 564 files. |
| Strict OpenSpec | Passed: 17 of 17 items before this evidence update. |
| Full server suite | One implementation-time run was intentionally interrupted after about two minutes with no observed failure; it is not recorded as a pass and remains due on the final fixed SHA. |

Two independent fixed-SHA reviews found no P0-P2 issue. The Standards review's
only P3 was a stale startup-order comment; the follow-up commit corrected it.
The specification review found tasks 2.1 through 2.4 complete. Agent review is
supporting evidence, not CI or release approval.

## Bounded server history evidence

The revision list now has one typed summary-page port and a projected SQLite
keyset query ordered by `(revision_number DESC, id DESC)`. It independently
validates 1 through 100, fetches at most `limit + 1`, and emits only the seven
summary columns. SQL evidence shows the existing
`uq_document_revision_number` index and no temporary sort; neither body nor
metadata appears in the statement.

Authenticated cursor validation covers malformed alphabet, padding, fatal
UTF-8, truncation, non-canonical JSON, unknown version, invalid or unsafe
revision number, empty or overlong id, and cross-project/document identity.
Invalid and repeated query values return 422 before any Store call. The route
authenticates before both schema and semantic validation, while a valid cursor
against a missing or foreign document retains scoped 404. A deleted boundary
row continues from its positional tuple and a concurrently inserted newer row
does not enter the older traversal.

Restore remains independent from list payloads: a historic summary id causes
one scoped full-revision read, then creates a new restore revision whose body
and metadata are exactly the historic values and whose parent is the current
base. Stale bases create no revision and cross-document ids remain 404.

| Validation surface | Result |
|---|---|
| Server pagination and related revision regressions | Passed: 9 files and 77 tests on the implementation; review repair passed 7 files and 37 tests. |
| Server type-check, lint, architecture, build, and gates | Passed; final repair checked 219 modules / 907 dependencies and 571 size-gated files. |
| OpenAPI and generated frontend type drift | Passed; the bounded query and summary-only response match generated artifacts. |
| Frontend type-check | Passed after generated type refresh; handwritten History behavior remains intentionally pending. |

Independent specification review found tasks 1.1 through 1.3 and 3.1 through
3.4 complete. Standards review found two P3 maintainability risks: duplicated
canonical cursor machinery and a test helper that silently returned only the
first page. The repair extracted a shared interface-layer codec while keeping
route-specific tuple validation, pinned Job and Revision wire tokens, and made
the test helper traverse to a null cursor with 101-row coverage. Follow-up
review found both issues closed with no P0-P3 finding.

## Bounded frontend history evidence

The frontend API now parses only the required revision-summary page, sends a
bounded first page of 50, and requires an explicit nullable continuation
cursor. History state is scoped by project and document, coalesces the same
request for every mounted subscriber, rejects stale ownership, appends older
pages without duplicates, and replaces rather than bridges a fresh-page gap.
Autosave, proposal acceptance, and restore refresh only the cursorless first
page and use the created revision id as causal ownership; none traverses older
pages.

Inactive acceleration is limited to eight owners when the active working set
fits that bound, temporarily retains only an unavoidable larger active set,
and converges after owner transitions or final unmount. Eviction aborts owned
requests, settles queued older work, removes subscribers, and clears per-owner
notification state. First-page and older-page failures are tracked
independently, so recovery of one intent cannot clear the other intent's still
unresolved error.

The History panel exposes a native `Load older revisions` button with distinct
loading, retry, and terminal states. Keyboard retry retains button focus; after
the terminal page, focus moves to the `Revision history` heading.

| Validation surface | Result |
|---|---|
| Frontend unit suite | Passed: 71 files and 408 tests on the final error-ownership repair. |
| Frontend lint, format, type-check, build, identity, and generated API drift | Passed. |
| React static diagnostics | Passed: score 100 with zero diagnostics. |
| Independent fixed-SHA Standards review | Clean: no P0-P3 finding; 4 focused files and 27 tests passed. |
| Independent fixed-SHA Spec/UX review | Clean: no P0-P3 finding; 10 related files and 79 tests passed; tasks 4.1 through 4.5 accepted. |
| Real Playwright History workflow | Pending task 5.2 integrated validation. |

## Current release boundary

Task 5 remains open. Required GitHub checks were not run because this task did
not push or open a pull request. The change remains active and unarchived until
the integrated browser/full-suite validation is complete and required CI is
green on the integration SHA.
