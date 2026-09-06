# Validation evidence

## Fixed points

- Comparison SHA: `3ef18a10fa91cef34b35a3df26f2587ab3fd114f`
- Change proposal SHA: `99fe121e829a035c45442c38467d3681a45a683d`
- Local implementation candidate SHA: `45faf2b254ddb4bb2bd8a046e63a2874a5061847`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Red, green, and review evidence

The production-store regression first created 32,766 real documents and
revisions and called `ExportStorePart.recordCompletedExportJob`. Against the
single-statement implementation it failed at the expected success assertion
with `SqliteError: too many SQL variables`.

The implementation now validates fixed groups of 500 revision identifiers.
Every group uses the transaction handle already owned by the same immediate
export landing, and only the complete aggregate can authorize snapshot reuse or
creation. No port, schema, migration, HTTP shape, or public error was changed.

The final production-path regression uses one incremental real database and
fully lands exports at 32,765, 32,766, and 32,767 documents. For every boundary
it checks exact snapshot-document cardinality and compares the full persisted
projection with the captured source. Before the successful landings it proves:

- duplicate document and revision identities remain visible invariant errors;
- a missing identity in a later group remains `ExportSourceInvalidatedError`;
- persisted immutable-content mutation remains a visible invariant error;
- every rejected source leaves zero snapshot, snapshot-document, artifact,
  Job, or event evidence.

Three independent agents separated RED construction, production implementation,
and read-only review. The final reviewer found no P0-P3 issue and confirmed the
501-binding maximum, compound ownership checks, same-transaction call chain,
error classification, source-order preservation, and file-size compliance.
Agent review is supporting evidence only; it is not CI or human acceptance.

## Local fixed-SHA evidence

All successful commands below ran against implementation SHA
`45faf2b254ddb4bb2bd8a046e63a2874a5061847`.

| Command | Result |
|---|---|
| Focused export regression set | Passed: 6 files and 13 tests, including capacity, transactions, source invalidation, and retry atomicity. |
| `pnpm --dir server exec vitest run --maxWorkers=4` | Passed: 144 files and 1,025 tests in 145.19 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 490-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 342 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 193 modules and 797 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm test:e2e:full-audit` from `frontend/` | Passed: all 8 Chromium workflows, including byte-faithful export/download, in 23.8 seconds. |
| `pnpm spec:validate --strict` | Passed: eight active changes plus the canonical specification, 9 of 9 items. |

## Archive and external gates

This locally completed change remains **active and not archived**. Required
GitHub checks did not run because this task did not push or open a pull request.
The repository maintainer must obtain required CI on the exact candidate SHA,
then merge the modified requirement into the canonical specification and
archive through the repository workflow. Cross-platform execution outside this
Darwin arm64 host and human acceptance were not run and are not implied by
automated or agent review.

Artifact memory budgets, legacy-import limits/TOCTOU, retry idempotency, and
proposal attempt identity remain separate findings; this change does not claim
to solve them.
