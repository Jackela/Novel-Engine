## Why

A pending conflict reload can return after the author restores a historical Revision. The old read replaces the restored version and can silently discard text or title entered after that restore.

## What Changes

- Ignore a pending latest-version read if the same active Document has accepted another Revision since that read began.
- Preserve the later accepted Revision and any subsequent Draft; retain ordinary reload and explicit restore behavior.
- Prevent a superseded autosave recovery read or failure from reinstating an obsolete conflict after a later restore.

## Impact

A narrow Studio frontend concurrency correction and regression coverage. No API, persistence, dependency, workflow, or design-language change.
