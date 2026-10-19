## Why

Known Review and Export failures carry null result IDs. The Studio currently rejects these valid terminal Jobs, hiding their actual failure and retaining a settled retry key.

## What Changes

- Recognize null Review and Export result IDs in valid complete failed Jobs while preserving validation of malformed values.
- Allow a known terminal failed retry to settle and clear its attempt key, so the next explicit author retry starts a new attempt.

## Impact

Studio frontend behavior and focused regressions only. No API, database, dependency, design-language, or deployment change. Existing saved-Revision workflows remain in place.
