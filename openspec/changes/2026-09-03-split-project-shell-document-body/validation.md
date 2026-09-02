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

`GET /api/projects/:projectId` uses one `readProjectShell` application/store
seam. Its real SQLite projection executes a scoped project read, one ordered
document-summary query, and one ordered volume query. The summary query selects
no Markdown, metadata JSON, or revision source. Project creation serializes its
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
contains no body, metadata, or revision-source hydration.

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

## Current boundary

Tasks 1 and 2 are locally evidenced on the implementation SHA. Frontend state,
lazy Inspector ownership, browser workflows, independent fixed-SHA reviews,
and required CI remain open. This change stays active and unarchived; local
tests and generated artifacts are not release approval.
