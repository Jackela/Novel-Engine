# Validation evidence

## Fixed points

- Comparison SHA: `7a44442bcef4747a8cd18b989ddc91c184e38ef2`
- Change proposal SHA: `346e43e6d74f93989ef8c0771cbe533eae438127`
- Final export implementation candidate SHA:
  `2b9b026f31f685b1f4b53a07edb6cdc24a3b5373`
- Fixed-SHA worktree:
  `/Users/jackela/Documents/GitHub/Novel-Engine-wave26-fixed-2b9b026f`
- Environment: Darwin arm64, Node.js 24.19.0, pnpm 11.6.0, Vitest 4.1.11

## Targeted and review evidence

The implementation bounds source capture, all three renderers, publication
proof/recovery, retry evidence, and artifact response lifetime. Exact and
plus-one tests cover 65,536 source documents, 16,777,216 UTF-8 source bytes,
67,108,864 artifact bytes, 16,384 manifest bytes, and the 134,217,728-byte
application download pool. Descriptor tests cover no-follow open, sparse and
growing files, truncation, replacement, checksum mismatch, short reads, and
allocation only after type and size proof. Renderer permits and download
reservations release generation-safely on success, failure, rollback, response
finish, disconnect, and the late-listener race.

The first shared-tree full server run exposed a real response-schema regression:
invalid retry idempotency headers produced a Fastify serialization 500 because
the exact 422 union omitted `VALIDATION_ERROR`. The implementation added that
closed validation branch, regenerated OpenAPI and frontend types, and the
focused retry/capacity suite then passed 20 of 20 tests. The final targeted
download/retry/capacity set passed 9 files and 37 tests.

Independent security review first found a disconnect-before-listener capacity
leak and generic OpenAPI/retry-response evidence. Follow-up review found all
three closed: response/request/socket preclosed state is checked around send,
download errors have exact JSON schemas, and same-key retry replays byte-identical
422 evidence without another source read, Job, event, snapshot, or artifact.
Agent review supports but does not replace fixed-SHA validation or CI.

## Local fixed-SHA evidence

All successful commands below ran against the clean tracked tree at
`2b9b026f31f685b1f4b53a07edb6cdc24a3b5373` in the isolated worktree.

| Validation surface | Result |
|---|---|
| Full server tests | Passed: 174 files and 1,171 tests in 269.07 seconds. |
| Server gates | Passed: SSOT, hygiene, 537-file size budget, migration channel, llms-txt, and OpenAPI snapshot. |
| Server build | Passed with `tsc -p tsconfig.build.json`. |
| Full frontend unit tests | Passed: 67 files and 368 tests in 19.24 seconds. |
| Frontend production build | Passed: 1,913 modules; Novel Engine 0.6.0 identity verified in HTML and 7 JavaScript bundles. |
| TypeScript-backend Playwright workflows | Passed: 8 of 8 in 22.9 seconds. |
| API-types drift | Passed; generated types match the OpenAPI snapshot. |
| Strict OpenSpec | Passed: 13 of 13 active changes/specification items. |

The isolated worktree's first package-script attempt stopped before tests with
`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY` because pnpm tried to rebuild a
reused dependency directory without a TTY. No dependency tree was deleted or
rewritten. The validator then invoked the repository's already-installed,
version-matched package binaries from the fixed worktree working directory;
the product tests above all completed successfully. An untracked dependency
symlink was validation harness state, not a product change.

## Named later changes

This change does not claim to bound unrelated catalogs or startup recovery
enumeration. Project/export catalogs and publication-recovery directory scans
still need their own pagination/enumeration contracts. Source capture also
retains grouped query result arrays until the synchronous transaction returns;
immediate per-group disposal is a separate P2 memory optimization. These are
named later changes because changing discovery, cursors, or transaction
ownership would broaden this P1 resource-lifecycle contract.

## Archive, external, and human gates

This locally completed change remains **active and not archived**. Required
GitHub checks were not run because this task did not push or open a pull
request. Owner: repository maintainer. Closure: every live required context is
green on the exact integration SHA, then merge the delta into the canonical
specification and archive the change.

Cross-platform execution and a target-container persistence restart were not
run on this candidate. Owner: release maintainer. Closure: required CI executes
those surfaces on the final integration SHA. A separate visual or accessibility
acceptance is not applicable because the change adds no interface or copy;
release authorization remains owner-required and is not implied by local tests.
