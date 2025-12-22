# Design: Filesystem Guest Workspaces

## Goals
- Guest-first: no login required for core functionality.
- Durable: atomic writes, crash safety, recoverable state.
- Isolated: a session cannot read/write another session’s workspace.
- Inspectable: files are human-readable where feasible; include a manifest and version.

## Workspace Identity
- Workspace ID is generated server-side and stored in a cookie (or equivalent first-party storage).
- The backend scopes all operations to the workspace resolved from the request.

## On-Disk Layout (proposed)
```
data/workspaces/<workspace_id>/
  manifest.json            # schemaVersion, createdAt, lastAccessedAt
  characters/
    <character_id>.json
  runs/
    <run_id>.json
  narratives/
    <narrative_id>.json
  exports/                 # optional staging
```

## Atomic Writes
- Writes MUST be atomic (write to temp file, fsync, rename).
- Corruption recovery MUST prefer last-known-good files and surface a clear error when recovery is impossible.

## Lifecycle
- Guest workspaces can expire after a configurable TTL, but export/import is always available before cleanup.

