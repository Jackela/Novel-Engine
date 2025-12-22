# Proposal: Add Guest Workspaces Backed by the Filesystem

## Why
- The product already supports a “guest/demo” entry in the frontend, but persistence is not formalized: data layout, session boundaries, and durability guarantees are implicit.
- A filesystem-backed workspace is the simplest long-term persistence layer for this project (no DB requirement) while still enabling correctness: isolation, atomic writes, schema versioning, export/import.
- “Real usable” frontend flows require reliable persistence across refreshes and sessions, especially in guest mode.

## What Changes
1. **Session → workspace mapping**
   - A guest session creates (or resumes) a filesystem workspace, and all user-created artifacts (characters, runs, narratives) are scoped to that workspace.
2. **Filesystem store with durability guarantees**
   - Define an on-disk layout, schema versioning, atomic writes, and recovery behavior.
3. **Workspace lifecycle**
   - Add lifecycle rules for guests (TTL/cleanup) and explicit export/import for portability.
4. **Character-service alignment**
   - Treat “guest session” as a valid authenticated session boundary for character CRUD and simulations.

## Impact
- Establishes a durable persistence foundation without introducing a database.
- Provides a clear contract for backend and frontend to share (workspace identity + isolation).

## Dependencies
- Should follow `standardize-api-surface`.
- Benefits from `refactor-backend-api-platform` so persistence is behind interfaces.

