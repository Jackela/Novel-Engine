# Preserve writing failure state

## Why

Current main can drop the unsaved-change guard while a newer local Draft survives a delayed/failed body reload; successful Review retries remain hidden behind a cached older assessment; synchronous DashScope Responses can mark failed or incomplete generation as completed when structured prose is present. Each has a baseline reproducer using synthetic data.

## What Changes

- Keep current-owner unaccepted Draft guidance and close/refresh protection during accepted-body reloads by reusing the accepted save baseline.
- Invalidate Review history after a completed Review retry, preserving lazy activation and independent Jobs recovery.
- Reject documented non-completed synchronous DashScope Responses before Proposal success, retaining existing successful and omitted-status compatibility.

## Impact

No feature addition/removal, main workflow redesign, new dependency, migration, public API shape or deployment change. Drafts remain component-local; conflicts keep explicit author resolution; Review/Export still use accepted revisions; Proposal application still requires explicit acceptance. Verification uses synthetic data and deterministic/controlled providers, not real supplier credentials.
