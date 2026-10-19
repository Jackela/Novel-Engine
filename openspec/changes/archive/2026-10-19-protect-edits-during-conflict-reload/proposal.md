## Why

A conflict reload currently replaces text and title typed after the author chose to discard the earlier Draft. Preserve those newer edits while retaining the existing explicit discard workflow.

## What Changes

- Retain edits made while loading the latest conflicting Document as an editable conflict against the returned accepted revision.
- Keep the existing discard behavior when no edit follows the explicit reload choice.

## Impact

Studio frontend behavior and focused regressions only. No API, database, dependency, design-language, or deployment change. Existing saved-Revision workflows remain in place.
