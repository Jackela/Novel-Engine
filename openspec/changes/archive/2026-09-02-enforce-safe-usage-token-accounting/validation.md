# Validation evidence

## Fixed points

- Comparison SHA: `fa5a362c48e27b51bee3d07f39eb25857561d3af`
- Change proposal SHA: `7a44442bcef4747a8cd18b989ddc91c184e38ef2`
- Implementation and local evidence candidate SHA:
  `daf3f7c5f185be28aa0819f5b6fca24e8ebc1bd3`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Red, green, and review evidence

Provider usage previously accepted unsafe integers such as `1e308`; multiple
otherwise valid rows could then aggregate beyond JavaScript's exact range and
serialize a non-finite total as JSON `null`. Direct store calls also bypassed
provider normalization.

The implementation now accepts only non-negative safe integers at the provider
and application boundaries, falling back to the unified word count for invalid
optional provider usage. The usage writer repeats the invariant inside the
caller-owned Job transaction. Generated migration `0018` adds SQLite integer,
range, and type checks without hand-edited metadata. Aggregates are read as
exact decimal text and converted or added only after safe-range validation;
historical corruption remains an opaque failure instead of rounded or null
accounting.

Two implementation agents separately owned provider/application normalization
and persistence/migration/aggregation. Their combined tests cover synchronous
and streaming OpenAI-compatible and DashScope results, injected provider
outcomes, retries, transaction rollback, migration failure, daily totals, and
HTTP corruption behavior. Agent review supports but does not replace CI.

## Local fixed-SHA evidence

All successful commands below ran against the clean committed tree at
`daf3f7c5f185be28aa0819f5b6fca24e8ebc1bd3`.

| Command | Result |
|---|---|
| Focused provider, application, retry, persistence, migration, and usage regressions | Passed: 11 files and 102 tests in 19.45 seconds. |
| `pnpm --dir server test` | Passed: 157 files and 1,114 tests in 266.15 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 513-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 360 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 197 modules and 820 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm spec:validate --strict` | Passed: twelve active changes plus the canonical specification, 13 of 13 items. |

## Archive and external gates

This locally completed change remains **active and not archived**. Required
GitHub checks did not run because this task did not push or open a pull request.
The maintainer must obtain required CI on the exact candidate SHA before merging
the modified requirements into the canonical specification and archiving the
change. Cross-platform execution and human acceptance were not run.
