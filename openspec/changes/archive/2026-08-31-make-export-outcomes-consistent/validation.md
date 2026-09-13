# Validation evidence

## Fixed points

- Comparison SHA: `0dd2c25f6d0f01934755a0cad79ab784aa873e34`
- Candidate SHA: `f3fac998170e012082c5f532ea5c762cf952cb29`
- Environment: macOS 27.0 arm64, Node.js 24.19.0, pnpm 11.6.0

## Targeted evidence

Command:

```text
pnpm --dir server exec vitest run tests/api/data_directory_ownership.test.ts tests/api/export_acknowledgement_failure.test.ts tests/api/export_publication_restart.test.ts tests/api/export_publication_cleanup_restart.test.ts tests/api/project_deletion_concurrency.test.ts tests/api/project_deletion_proposal_lifecycle.test.ts tests/api/project_deletion_retry_concurrency.test.ts tests/api/proposal_stream_resource_lifecycle.test.ts tests/contexts/export_artifact_publication_ownership.test.ts tests/contexts/export_publication_cleanup_journal_recovery.test.ts tests/contexts/project_artifact_files.test.ts tests/db/startup_pipeline.test.ts
```

Result: passed, 12 files and 66 tests. This covers the write-ahead cleanup
intent, restart ordering, exact-inode recovery, post-commit acknowledgement
failure, process ownership, project deletion exclusion, provider disposal,
parent/leaf replacement, and connection initialization cleanup.

Three independent read-only review streams examined storage lifecycle,
OpenSpec/ADR conformance, and recovery test gaps. Their confirmed findings were
reproduced and fixed by the integrator; the final review reported no remaining
P0-P3 finding. Agent review remains supporting evidence, not a validation gate.

## Local full evidence

| Command | Result |
|---|---|
| `pnpm --dir server gates && pnpm --dir server arch && pnpm --dir server type-check && pnpm --dir server lint && pnpm --dir server test && pnpm --dir server build` | Passed; 112 test files, 876 tests; 179 modules and 748 dependencies had no architecture violation. |
| `pnpm --dir frontend lint && pnpm --dir frontend format:check && pnpm --dir frontend type-check && pnpm --dir frontend test:unit && pnpm --dir frontend build && pnpm --dir frontend check:api-types && pnpm spec:validate` | Passed; 54 test files, 272 tests; production build identity, generated API drift, and strict OpenSpec validation passed. |
| `pnpm --dir frontend test:e2e:ts` | Passed; 8 Chromium workflows against the emitted TypeScript server. |
| `pnpm --dir frontend exec react-doctor --json` | Passed; 0 diagnostics, score 100. |
| `pnpm audit --audit-level high --prod` | Passed; no known production dependency vulnerabilities. |

## External and human gates

- Docker container persistence/restart/deep-link validation: **not run** because
  the local host has no Docker executable. Residual risk is Linux container and
  volume behavior. Owner: repository CI. Closure: the `container` workflow job
  passes on the final review SHA.
- GitHub required checks: **not run** because this local task did not push or
  open a pull request. Residual risk is CI-only platform behavior and required
  context configuration. Owner: repository maintainer. Closure: every live
  required check is green on the integration SHA.
- Human acceptance: **not run** and not represented as approved. The change is
  primarily persistence and lifecycle behavior; local browser automation is
  supporting evidence only. Owner: release maintainer. Closure: explicit human
  release approval if the target release requires it.
