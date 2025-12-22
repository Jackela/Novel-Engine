# Tasks: Add Filesystem Guest Workspaces

## 1. Define workspace contract
- [ ] Decide workspace identifier format, TTL policy, and request binding (cookie/header).
- [ ] Define the on-disk layout and the manifest/schemaVersion fields.

## 2. Implement filesystem workspace store
- [ ] Introduce store interfaces (workspace, characters, runs) and a filesystem implementation.
- [ ] Implement atomic write utilities and safe path handling (prevent traversal).
- [ ] Implement list/get/put/delete behavior for characters inside a workspace.

## 3. Add session bootstrap + lifecycle
- [ ] Add an endpoint/middleware to create or resume a guest session and resolve workspace.
- [ ] Add TTL cleanup logic (manual command or scheduled job) with safety rails.
- [ ] Add export/import for workspace portability (zip or tar).

## 4. Tests and validation
- [ ] Add unit tests for atomic write + path safety.
- [ ] Add integration tests for session isolation (two sessions cannot see each other’s characters).
- [ ] Run full CI suite and `openspec validate add-filesystem-guest-workspaces --strict`.
