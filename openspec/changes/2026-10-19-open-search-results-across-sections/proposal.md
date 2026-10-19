## Why

Project search returns every Document kind, but the Outline, Characters and
World sections restrict their active Document. Selecting a hit of another kind
currently leaves the previous text visible and never delivers the locate intent.

## What Changes

- Selecting a cross-kind hit from a restricted section opens it in the existing
  Manuscript section, preserving the selected Inspector and locate intent.
- A hit compatible with the current section keeps that section.
- Reuse the existing section-kind constraint; do not change ordinary navigation.

## Impact

Local Studio navigation correction only. No API, persistence, dependency,
design-language or product-capability change.
