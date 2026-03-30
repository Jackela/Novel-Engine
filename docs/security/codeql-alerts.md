# CodeQL Alert Review

This repository keeps CodeQL focused on the active product surface under `src/apps/`, `src/contexts/ai/`, `src/contexts/narrative/`, `src/shared/`, `frontend/src/`, and the non-evaluation scripts used by the current engine.

Legacy subsystems under `src/contexts/world/`, `src/contexts/character/`, `src/contexts/knowledge/`, `src/api/`, `src/caching/`, `src/events/`, and the older test/evaluation trees are treated as historical support code and are excluded from the canonical scan scope.

Current review outcomes:

- Alerts on deleted or renamed paths from earlier scans are treated as stale history, not live findings in the current tree.
- The only source-level issue that needed a fix in this pass was `src/events/outbox.py`, where ordering now has an explicit equality method and deterministic sort key.
- Generated output, build artifacts, and dependency caches are excluded through `.github/codeql/codeql-config.yml`.

Policy:

- Confirmed false positives are documented here before any suppression is added or any scope exclusion is changed.
- If a future scan surfaces a real source-level finding, fix the code first.
- Only use code scanning suppressions when the finding is reviewed and confirmed to be a false positive.
