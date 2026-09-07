# Change: make proposal context coherent

## Why

Proposal generation currently resolves the target revision, project documents,
outline/beat, volumes, and Lore through separate store transactions. A commit
from another SQLite connection between those reads can therefore produce a
prompt that never represented one database state. Proposal retries have a
second ambiguity: the retry Job inherits `base_revision_id` A from its source,
but generation resolves the target's current revision B and may record a mix of
A and B across request, result, and usage evidence.

## What Changes

- Capture every database-owned proposal input in one coherent read transaction
  and hand the application an immutable context value.
- Make synchronous, streaming, and retry generation consume that same captured
  value without returning to the store while assembling the task.
- Keep a proposal retry pinned to the inherited `base_revision_id`; never
  silently rebase it onto a newer target revision.
- If the target has advanced, finish the new retry Job as a stable failed
  attempt before prompt assembly or Provider construction, preserving the
  original base and recording the captured current revision.
- Prove snapshot isolation with a deterministic two-connection SQLite
  interleaving test and prove entry-point parity and Provider/SSE ordering.

## Impact

- Affected server surfaces: the StudioStore proposal-context port and Drizzle
  adapter, resident/Lore input derivation, synchronous and streaming proposal
  services, and proposal retry execution/evidence.
- Public proposal success payloads, routes, prompt bytes, prompt-data escaping,
  generation capacity, Lore matching/promotion, and proposal acceptance remain
  unchanged.
- A stale proposal retry now returns its newly created terminal failed Job
  instead of generating from an undeclared newer base. The source Job remains
  immutable and a fresh proposal request remains available for the newer
  revision.
- No database migration, dependency, environment setting, or frontend change is
  required.
- Project-detail decomposition and project/job/review/export catalog pagination
  remain separate resource-capacity changes and are not addressed here.
