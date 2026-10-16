## Why

Authors can lose retained history after folded autosaves, receive an internal
error for an ordinary title collision, and receive misleading Lore wizard
results after a partial confirmation. Unchanged oversized Drafts also keep
issuing saves that cannot succeed. The fixes restore existing authoring and
recovery contracts without adding a product feature.

## What Changes

- Preserve the first Revision and the newest 200 actual retained rows.
- Return an atomic document conflict for a duplicate title.
- Reconcile confirmed Lore into navigation and retain per-candidate recovery.
- Stop automatic retries after permanent 413/422 save refusals while retaining the Draft and explicit recovery.

## Impact

No migration, dependency, deployment, provider configuration, or major workflow
change. Document PUT's documented 409 response now includes the existing
DOCUMENT_CONFLICT envelope; generated API types are regenerated. Local
navigation layout fixes keep existing actions and the DESIGN.md token system.
