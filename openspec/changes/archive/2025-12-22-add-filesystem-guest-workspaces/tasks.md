# Tasks: Add Filesystem Guest Workspaces

## 1. Define workspace contract
- [x] Decide workspace identifier format, TTL policy, and request binding (cookie/header).
- [x] Define the on-disk layout and the manifest/schemaVersion fields.

## 2. Implement filesystem workspace store
- [x] Introduce store interfaces (workspace, characters, runs) and a filesystem implementation.
- [x] Implement atomic write utilities and safe path handling (prevent traversal).
- [x] Implement list/get/put/delete behavior for characters inside a workspace.

## 3. Add session bootstrap + lifecycle
- [x] Add an endpoint/middleware to create or resume a guest session and resolve workspace.
- [x] Add TTL cleanup logic (manual command or scheduled job) with safety rails.
- [x] Add export/import for workspace portability (zip or tar).

## 4. Tests and validation
- [x] Add unit tests for atomic write + path safety.
- [x] Add integration tests for session isolation (two sessions cannot see each other’s characters).
- [x] Run full CI suite and `openspec validate add-filesystem-guest-workspaces --strict`.
