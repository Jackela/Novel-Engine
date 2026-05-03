# CodeQL Alert Review

The active CodeQL policy is defined in [.github/codeql/codeql-config.yml](../../.github/codeql/codeql-config.yml).

Effective scan scope:

- `src/`
- `scripts/`
- `frontend/`

Effective exclusions:

- `tests/**`
- `src/api/**`
- `src/caching/**`
- `src/contexts/character/**`
- `src/contexts/knowledge/**`
- `src/contexts/world/**`
- `src/events/**`
- `scripts/evaluation/**`
- generated output, caches, and build artifacts

Review notes:

- Alerts on deleted or renamed paths from earlier scans are stale history unless they reappear on a live path in the current tree.
- Confirmed false positives should be documented here before any suppression is added or any scope exclusion is changed.
- Fix the code first whenever a real source-level issue is found.

Policy:

- Only use code scanning suppressions when the finding is reviewed and confirmed to be a false positive.
