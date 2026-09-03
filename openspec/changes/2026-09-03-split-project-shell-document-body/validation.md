# Validation evidence

## Fixed points

- Comparison SHA: `2f7a0277cef5c19ad3ce22f8f6b2959beae352aa`
- Server shell/current-Document implementation SHA:
  `012afb997f844edbfd446644b8b846a2ec771a0c`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0,
  Vitest 4.1.11

## Server project-resource evidence

Contract-first API coverage initially failed all four scenarios: creation and
detail still returned complete bodies, the scoped GET route did not exist, an
anonymous request therefore reached the generic route 404, and reorder returned
complete Documents. The implementation now gives the shell, current Document,
and editor Draft distinct authority.

At fixed implementation SHA `012afb99`, `GET /api/projects/:projectId` used one `readProjectShell` application/store
seam. Its real SQLite projection executes a scoped project read, one ordered
document-summary query, and one ordered volume query. The summary query selects
no Markdown, metadata JSON, or revision source. That source exclusion is
historical evidence, not the current contract: the later whole-book integration
finding requires the lightweight closed revision source and reopens the affected
summary tests and implementation. Project creation at the fixed SHA serializes its
seed through the same exact summary builder. Whole-set reorder retains its
full-set validation and one transaction, then projects only ordered summaries.

`GET /api/projects/:projectId/documents/:documentId` authenticates in
pre-validation before the handler can call the Store. Its one scoped current
projection joins Owner, route project, target Document, and that Document's
current Revision. Missing, cross-project, and out-of-Owner requests all return
the byte-identical `NOT_FOUND` envelope with `Document not found.`; the route
never exposes an arbitrary historic Revision.

The public-route SQL observer attributes a successful request to exactly two
authentication statements plus its Studio projection. Shell projection uses
three statements independent of project size; current Document uses one, below
the two-statement ceiling. An anonymous syntactically valid current-Document
read emits no SQL. Query plans use the project/document/current-revision keys,
do not scan revision history, and require no temporary sort. Reorder tracing
contains no body, metadata, or revision-source hydration at that fixed SHA.

## Contract amendment after the fixed point

Whole-book resume plans directly from ordered document summaries and must skip
chapters whose current revision source is `ai-accepted`. The active contract now
requires the closed `revision_source` scalar on every summary while continuing
to exclude body and metadata JSON. This is workflow state, not body hydration.
Exact-shape, query projection, reorder, OpenAPI/type, and whole-book planning
tasks have been reopened and require new fixed-SHA evidence. No current pass is
claimed from the superseded `012afb99` projection.

## Revised server evidence

- Contract amendment SHA: `bbb48c3a404a32a0dfb96dbe5b826a8876877645`
- Current-revision pointer integrity SHA:
  `1f8657122b363a1dd3a2cb5dfd2d92856327972e`
- Revised server shell implementation SHA:
  `0a4ec30d649d0c4fcca8ba5cfdecd7d405aa3dfd`

The amended contract-first run failed 6 of 8 assertions across the API shell,
Store shell, and public-route query suites: creation, detail, and reorder lacked
the required source scalar, and the shell query did not select it. The revised
implementation projects only the current Revision's validated closed
`author | ai-accepted | restore` source together with revision identity and
exact word count. It still selects neither `content_markdown` nor
`metadata_json`. Creation, detail, and reorder share the same strict schema and
payload builder; the generated OpenAPI contract requires the source enum and
forbids extra fields on all three surfaces.

The security repair binds both new revision joins by revision id and owning
Document id. A forged authorized Document pointer to a different Owner's
Revision initially made both Store/API regressions fail by returning the
foreign body and false word count. The repaired current-Document resource now
returns the same scoped `NOT_FOUND` boundary, while the shell fails closed with
an opaque `INTERNAL_ERROR`; neither response contains the foreign body,
metadata sentinel, or count. Query budgets remain two fixed auth statements,
three shell projection statements, and at most two current-Document projection
statements, with indexed access and no revision-history scan.

The OpenAPI drift gate failed 1 of 1 before the deliberate baseline refresh.
After regeneration, the final focused run passed 7 files and 58 tests. The
first full server run passed 197 of 198 files and 1,254 of 1,255 tests; its only
failure was a superseded project-create assertion that still prohibited the
now-required source. After that assertion was updated, the second full run
passed 198 files and all 1,255 tests in 396.28 seconds.

| Revised validation surface | Result |
|---|---|
| Server lint and type-check | Passed: Biome checked 426 files; TypeScript reported no error. |
| Server architecture and build | Passed: 222 modules / 927 dependencies; production TypeScript build passed. |
| Server gates | Passed: SSOT, hygiene, 599-file size gate, migration channel, 19 llms-txt targets, and OpenAPI snapshot. |
| Generated frontend API types | Deliberately regenerated; drift check and frontend type-check passed. |
| Strict OpenSpec | Passed: 19 of 19 changes/specifications. |

| Validation surface | Result |
|---|---|
| Contract-first red | Expected failure: 1 file, 4 of 4 tests failed against the aggregate contract. |
| Full server suite after repair | Passed: 196 files and 1,251 tests in 301.73 seconds. |
| Server lint and type-check | Passed: Biome checked 423 files; TypeScript reported no error. |
| Server architecture and build | Passed: 221 modules / 923 dependencies; production TypeScript build passed. |
| Server gates | Passed: SSOT, hygiene, 589-file size gate, migration channel, 19 llms-txt targets, and OpenAPI snapshot. |
| OpenAPI and generated frontend types | Deliberately regenerated; drift check and frontend type-check passed. |

No schema migration, dependency, environment contract, historical Revision
read, Snapshot authority, save/restore/proposal response, or handwritten
frontend file changed in this server wave. The first full-suite run ended with
1,249 prior tests passing and one outdated beat fixture expecting an undefined
body from the new shell; the fixture was changed to follow the explicit current-
Document resource, passed 9 of 9 in isolation, and the second full suite passed
all 1,251 tests.

## Frontend shell and one-active Document evidence

Frontend contract parsing now treats project catalog rows, project shells,
Document summaries, and complete current Documents as four exact shapes. Shell
and reorder summary parsing reject body or metadata keys, current-Document
parsing rejects summary-only responses, counts require nonnegative integers,
and revision source is a required closed enum. The shared HTTP client reads the
selected current Document only from the scoped Document endpoint.

The editor owns at most one accepted body. An in-flight-only registry
coalesces exact `(project, Document, expected revision, lifecycle)` tuples,
fans the result out to surviving subscribers, suppresses released or obsolete
owners, and aborts only when the final subscriber releases. Successful bodies
are not retained globally. Pending and failed reads render no old or invented
body, retain navigation, and provide local Retry. Revision mismatches perform
one shell refresh and at most one replacement body read before a readable
churn failure.

The project shell is published before the existing Review and Export reads, so
active-body hydration is no longer blocked by those histories. Review and
Export are still fetched after shell publication in this wave; task 3.2 stays
open until task 4.1 gives both panels independent lazy owners. Draft/cache
separation and the complete mutation-reconciliation matrix also remain tasks
3.4 and 3.5 rather than being claimed by compatibility changes in this wave.

| Validation surface | Result |
|---|---|
| Contract/state-machine red tests | Expected failures observed before implementation: missing strict parsers/current endpoint and missing current-Document hook. |
| Frontend unit suite | Passed: 76 files and 428 tests. |
| Frontend lint, format, and type-check | Passed: Biome checked 199 files with no diagnostics; formatter checked 198 files; TypeScript reported no error. |
| Repository file-size gate | Passed: 599 files checked; every code file is at or below 300 code lines. |
| Frontend production build | Passed: Vite built 1,923 modules; build identity verified Novel Engine 0.6.0. |
| API-types drift | Passed: generated types match the current OpenAPI snapshot. |
| React Doctor | Passed: 186 files analyzed, score 100, zero diagnostics. |
| TypeScript-backend Studio smoke | Passed: 3 Chromium workflows covering owner setup/edit/proposal/search/deep links, login/error envelopes, and bounded History retry. |
| Strict OpenSpec | Passed: 19 items, zero failures. |

## Current boundary

Contract tasks 1.1–1.4 and server tasks 2.1–2.5 are evidenced on the revised
fixed SHAs. Whole-book planning task 1.5 remains owned by its frontend evidence;
frontend tasks 3.1 and 3.3 have current local evidence above. Lazy Inspector
ownership, mutation/Draft separation, the full browser matrix, independent
fixed-SHA reviews, and required CI remain open. This change stays active and
unarchived; local tests and generated artifacts are not release approval.

## Frontend ownership-race repair

- Fixed implementation SHA: `bc4b2783264a82127efdde53cfb80719558d2682`
- Comparison SHA: `eebfa7db0e078cf0c47fa89eded2a867aa8791ed`

Contract-first regressions failed in four places before the repair: a
summary-only change reacquired and aborted the same current-Document lease, a
foreign-project child summary still issued a body request, a late convergence
read replaced a concurrent narrow shell mutation, and the Studio shell owner
had no captured read/mutation epoch to reject that stale publication.

The repaired current-Document key is derived only from the exact scalar owner
tuple `(project id, Document id, expected revision id, lifecycle)`. Summary
reorder or Lore-only changes therefore retain the same lease. Child summaries
must belong to the route project before any body request is acquired, and a
body response must still match the project/Document tuple before it can be
accepted. Convergence reads now capture both a shell-read epoch and a local
shell-mutation epoch. A later local mutation makes the read ineligible to
publish; the current navigation remains visible and the editor exposes an
explicit Retry instead of replacing newer state or guessing at a merged shell.

| Validation surface at `bc4b2783` | Result |
|---|---|
| Focused ownership regressions | Passed: 4 files and 24 tests. |
| Full frontend unit suite | Passed: 78 files and 432 tests. |
| Frontend lint, format, and type-check | Passed: Biome checked 202 files, formatter checked 201 files, and TypeScript reported no error. |
| Frontend production build | Passed: Vite built 1,923 modules and verified Novel Engine 0.6.0 in HTML and seven JavaScript bundles. |
| API-types drift | Passed against the then-current OpenAPI snapshot. |
| React Doctor | Passed: score 100 and zero diagnostics. |
| Repository file-size gate | Passed: 608 files checked, with no code file over the 300-line budget. |
| TypeScript-backend Studio smoke | Passed: three Chromium workflows. |
| Strict OpenSpec | Passed: 19 items, zero failures. |

The validation worktree also contained separately owned, uncommitted project-
settings server/OpenAPI/generated-type changes. They were neither staged nor
included in `bc4b2783`; a later integrated fixed-point run must revalidate the
combined repository. Tasks 3.2, 3.4, 3.5, 5.2, 5.3, and 5.4 remain open.

## Shared convergence-cycle repair

- Superseding frontend implementation SHA:
  `d59a7b14c16a7b661ebab3c04bf47874fc01b40b`
- Comparison SHA: `bc4b2783264a82127efdde53cfb80719558d2682`

Independent re-review found that the first ownership repair coalesced only the
raw current-Document GET. Two equal-tuple subscribers still reacted to the
same unexpected revision independently, issuing two shell refreshes and
invalidating one another's read epoch. The new two-subscriber regression
failed at the comparison SHA because two project reads were observed where the
contract permits one.

The registry now owns one complete causal read cycle: initial current-Document
read, one shell refresh, and at most one replacement current-Document read.
The shell publication is a shared, memoized commit performed by the first
surviving subscriber, so releasing the initiating subscriber cannot suppress
the result and multiple survivors cannot repeat the publication. All survivors
receive the same terminal outcome. The shell mutation epoch remains decisive:
a concurrent local mutation still rejects the shared commit and leaves an
explicit Retry. Completed failures are keyed to the refreshed revision so a
render caused by shell publication cannot start an unbounded extra read; an
explicit Retry advances the attempt epoch.

| Validation surface at `d59a7b14` | Result |
|---|---|
| Focused ownership regressions | Passed: 4 files and 25 tests. |
| Full frontend unit suite | Passed: 78 files and 433 tests. |
| Frontend lint, format, and type-check | Passed: Biome checked 203 files, formatter checked 202 files, and TypeScript reported no error. |
| Frontend production build | Passed: Vite built 1,924 modules and verified Novel Engine 0.6.0 in HTML and seven JavaScript bundles. |
| API-types drift | Passed against the current OpenAPI snapshot. |
| React Doctor | Passed: score 100 and zero diagnostics. |
| Repository gates | Passed: SSOT, hygiene, 609-file size, migration-channel, llms-txt, and OpenAPI snapshot gates. |
| TypeScript-backend Studio smoke | Passed: three Chromium workflows. |
| Strict OpenSpec | Passed: 19 items, zero failures. |

This repair does not claim lazy Inspector ownership, mutation/Draft separation,
the complete browser matrix, independent fixed-SHA review closure, or CI.
Tasks 3.2, 3.4, 3.5, 5.2, 5.3, and 5.4 remain open.

## Unexpected convergence-failure repair

- Superseding frontend implementation SHA:
  `5f4203afe019479a4ca39fdb94ac594c0d0fd9f7`
- Comparison SHA: `d59a7b14c16a7b661ebab3c04bf47874fc01b40b`

Final standards review found that the shared-cycle Promise still had an empty
rejection handler. A programming error outside the cycle's structured HTTP and
contract outcomes could therefore leave every subscriber permanently loading
while erasing the diagnostic. The registry now converts one shared unexpected
rejection into an explicit broadcast outcome and reports the original Error
once through the browser's standard `reportError` channel, with a
`console.error` fallback where that channel is unavailable. Every surviving
subscriber leaves loading, receives a readable local Retry state, and shared
cleanup still runs through the settled Promise.

Shell publication is guarded the same way. If the authority callback throws,
its memoized shared commit reports the original Error once and returns an
unexpected terminal result instead of rethrowing independently from every
subscriber. Regressions cover both an authority capture/cycle rejection shared
by two subscribers and a shell-publication throw. They assert one diagnostic,
no permanent loading state, a readable error, and bounded request counts.

| Validation surface at `5f4203af` | Result |
|---|---|
| Focused current-Document regressions | Passed: 3 files and 17 tests. |
| Full frontend unit suite | Passed: 79 files and 435 tests. |
| Frontend lint, format, and type-check | Passed: Biome checked 205 files, formatter checked 204 files, and TypeScript reported no error. |
| Frontend production build | Passed: Vite built 1,925 modules and verified Novel Engine 0.6.0 in HTML and seven JavaScript bundles. |
| API-types drift | Passed against the current OpenAPI snapshot. |
| React Doctor | Passed: score 100 and zero diagnostics. |
| Repository gates | Passed: SSOT, hygiene, 611-file size, migration-channel, llms-txt, and OpenAPI snapshot gates. |
| TypeScript-backend Studio smoke | Passed: three Chromium workflows. |
| Strict OpenSpec | Passed: 19 items, zero failures. |

The repair does not change the open-task boundary. Tasks 3.2, 3.4, 3.5, 5.2,
5.3, and 5.4 remain open pending their separately required evidence.
