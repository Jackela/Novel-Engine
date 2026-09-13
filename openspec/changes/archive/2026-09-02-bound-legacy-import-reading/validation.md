# Validation evidence

## Fixed points

- Comparison SHA: `08f31733ef32b7d87971817146188ff6c4549c12`
- Change proposal SHA: `a14882366cb2b5a0494a20926391d9eea5b8dd31`
- Implementation and local evidence candidate SHA:
  `c373ce4f28a445b097c3d61dc076eaa07f333a72`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0

## Red, green, and review evidence

The original reader first inspected a path and later synchronously read that
path. Deterministic replacement tests reproduced outside-file consumption for
both `story.yaml` and a chapter. A bounded 128 MiB fixture also demonstrated
unbounded synchronous allocation and event-loop work before this change.

The implementation now opens each accepted source with no-follow semantics,
uses one descriptor for validation and bounded reads, compares path and handle
identity with bigint device/inode values, and revalidates source, manuscript,
and chapter-directory identities before returning. Path-shape races, including
an ancestor replaced by a regular file, become explicit domain failures rather
than raw I/O disclosure. A large accepted chapter yields to a scheduled event
loop turn while its read remains in progress.

Fixed raw-byte and count limits are 262,144 for `story.yaml`, 4,194,304 per
chapter, 67,108,864 for the accepted workspace, 2,000 chapters, and 4,096
observed chapter-directory entries. Exact-limit and limit-plus-one tests cover
all five resources, including multibyte UTF-8 and non-matching entries. Capacity
failure maps to HTTP 422 `IMPORT_CAPACITY_EXCEEDED` with only `resource`,
`limit`, and `observed`; authentication and confinement remain earlier gates.

Import waits for the complete filesystem read before store access. Repeated
source hashes remain owner-scoped and return the existing project without
loading its documents or volumes. CLI import awaits completion before closing
SQLite and emits only a bounded project summary with an explicit `created`
signal; its output does not grow with chapter Markdown.

Three agents separately implemented and reviewed the filesystem/application,
HTTP/OpenAPI, and CLI boundaries. A later adversarial wave found and closed
unsafe-number inode comparison and raw `ENOTDIR` propagation. The root review
also regenerated the frontend API types and reran the combined gates. Agent
review supports but does not replace CI or human acceptance.

## Local fixed-SHA evidence

All commands below ran against the clean committed tree at
`c373ce4f28a445b097c3d61dc076eaa07f333a72`.

| Command | Result |
|---|---|
| Focused reader, identity, budget, application, HTTP, and CLI regressions | Passed: 6 files and 40 tests in 12.53 seconds. |
| `pnpm --dir server test` | Passed: 153 files and 1,071 tests in 315.62 seconds. |
| `pnpm --dir server gates` | Passed; SSOT, hygiene, 508-file size budget, migration channel, 19 llms-txt links, and OpenAPI snapshot were clean. |
| `pnpm --dir server type-check` | Passed. |
| `pnpm --dir server lint` | Passed; 355 files checked with no fixes. |
| `pnpm --dir server arch` | Passed; 196 modules and 817 dependencies had no violation. |
| `pnpm --dir server build` | Passed. |
| `pnpm --dir frontend test:unit` | Passed: 67 files and 368 tests in 39.09 seconds. |
| `pnpm --dir frontend lint` | Passed; 179 files checked with no fixes. |
| `pnpm --dir frontend format:check` | Passed; 178 files checked with no fixes. |
| `pnpm --dir frontend type-check` | Passed. |
| `pnpm --dir frontend check:api-types` | Passed; generated types match the OpenAPI snapshot. |
| `pnpm --dir frontend build` | Passed; 1,913 modules built and Novel Engine 0.6.0 identity was verified in HTML and seven JavaScript bundles. |
| `pnpm test:e2e:full-audit` from `frontend/` | Passed: all 8 Chromium workflows in 23.3 seconds. |
| `pnpm spec:validate --strict` | Passed: ten active changes plus the canonical specification, 11 of 11 items. |

## Archive and external gates

This locally completed change remains **active and not archived**. Required
GitHub checks did not run because this task did not push or open a pull request.
The repository maintainer must obtain required CI on the exact candidate SHA,
complete compatibility review, merge the modified requirements into the
canonical specification, and archive through the repository workflow.

Cross-platform execution outside this Darwin arm64 host and human acceptance
were not run. Project/revision pagination, export artifact size policy, and lore
prompt capacity remain separate findings; this change does not claim to solve
them.
