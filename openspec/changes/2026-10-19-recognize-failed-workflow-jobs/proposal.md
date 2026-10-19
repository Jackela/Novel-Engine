## Why

Known first-run Review and Export failures carry null result IDs. The Studio currently rejects these valid terminal Jobs, hiding their recorded failure in creation responses and complete Job details.

## What Changes

- Recognize null Review and Export result IDs in valid complete failed Jobs only for the matching failed Job kind, while preserving rejection of null IDs on completed or unrelated Jobs and other malformed values.
- Preserve existing retry-attempt handling when a complete terminal Job carries a valid nullable result ID. Current backend retry reservations start with an empty result and their ordinary failure path already works.

## Impact

Studio frontend contract parsing and focused regressions only. No API, database, dependency, design-language, or deployment change. Existing saved-Revision workflows and retry-key ownership remain in place.
