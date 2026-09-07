# Validation evidence

## Fixed points

- Comparison SHA: `26e4c57cd4601ea829b3e04483d84075599277c5`
- Change proposal SHA: `b629ca75f046f8cf70762fc75ff9c170303c5fef`
- Implementation SHA: `af509d518be6a3aff625c53f40a4d3facb095f10`
- Local evidence candidate SHA: `69d7c81a371d0c4837191fd972a649ce42b92cbc`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Red, green, and review evidence

The contract-first HTTP test initially produced four expected failures: the
route accepted a missing key, a running replay omitted `Retry-After`, and a
terminal replay created another Job. Existing API tests then exposed every
legacy caller that had not migrated to the new required header. The migrated
tests pass explicit scenario-owned keys; no shared helper fabricates a default.

The final implementation reserves a retry Job and its first event in one
immediate transaction under a generated partial unique project/source/key
index. Only the reservation creator executes work. A terminal replay returns
the exact persisted full Job, while a running replay returns the existing 409
with `Retry-After: 1`. A project-exclusive precheck preserves the established
409 throughout committed deletion cleanup without making terminal replay
consume provider capacity.

The browser registry binds an attempt to authenticated session, owner, project,
and source Job. It writes a cryptographic UUID before dispatch, retains it for
ambiguous outcomes and navigation, clears only the exact settled attempt, and
clears the complete registry at logout intent or session replacement. Focused
tests cover double activation, response loss, reload, A-B-A navigation, late
settlement, and definitive versus ambiguous HTTP outcomes.

Three independent agents implemented the store/application path, the frontend
registry, and the initial HTTP failures, then crossed those boundaries in
read-only review. Review found and closed the logout-response-loss cleanup gap,
the project-deletion error-order regression, and the legacy test migration.
An additional evidence wave proves completed and failed proposal, review, and
export replays do not repeat provider, usage, snapshot, review, issue, render,
artifact, Job, or event evidence. Agent review is supporting evidence only; it
is not CI or human acceptance.

## Local fixed-SHA evidence

All successful commands below ran against the clean committed tree at
`69d7c81a371d0c4837191fd972a649ce42b92cbc`.

| Command | Result |
|---|---|
| Focused retry identity and replay evidence | Passed: three new evidence files and 11 tests, plus the HTTP/store/restart and existing operation regressions. |
| `pnpm --dir server exec vitest run --maxWorkers=4` | Passed: 149 files and 1,047 tests in 151.78 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 503-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 350 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 195 modules and 810 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed: 67 files and 368 tests in 21.08 seconds. |
| `pnpm --dir frontend lint` | Passed; 179 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 178 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend check:api-types` | Passed; generated types match the OpenAPI snapshot. |
| `pnpm --dir frontend build` | Passed; 1,913 modules built and Novel Engine 0.6.0 identity was verified in HTML and seven JavaScript bundles. |
| `pnpm test:e2e:full-audit` from `frontend/` | Passed: all 8 Chromium workflows in 22.8 seconds. |
| `pnpm spec:validate --strict` | Passed: nine active changes plus the canonical specification, 10 of 10 items. |

## Archive and external gates

This locally completed change remains **active and not archived**. Required
GitHub checks did not run because this task did not push or open a pull request.
The repository maintainer must obtain required CI on the exact candidate SHA,
complete compatibility review, merge the modified requirement into the
canonical specification, and archive through the repository workflow.

Cross-platform execution outside this Darwin arm64 host and human acceptance
were not run and are not implied by automated accessibility, browser, or agent
review. Artifact memory budgets and legacy-import size/count/TOCTOU boundaries
remain separate findings; this change does not claim to solve them.
