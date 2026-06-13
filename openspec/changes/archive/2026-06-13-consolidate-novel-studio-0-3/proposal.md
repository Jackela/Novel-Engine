# Consolidate Novel Studio 0.3

## Why

The repository currently exposes multiple product identities, multiple version
values, a CLI-first manuscript model, and browser surfaces that cannot edit the
manuscript they claim to manage. Novel Studio 0.3.0 establishes one shippable
product, one version source, one product specification, and one authoritative
content store.

## What Changes

- Make the self-hosted Web Studio the only authoring product.
- Replace file-backed authoring state with a SQLite revision store.
- Add project, document, revision, snapshot, review, export, search, and job APIs.
- Add a complete manuscript editor with outline, character, world, history,
  review, export, and settings surfaces.
- Keep AI changes proposal-only until the author explicitly accepts them.
- Support deterministic Markdown, DOCX, and EPUB exports from immutable
  snapshots.
- Provide a one-time, idempotent importer for legacy file workspaces.
- Reduce the CLI to operational commands.
- Remove old StoryForge, multi-agent, RPG character, generic knowledge, and
  CLI-authoring product surfaces.
- Make `pyproject.toml` the only editable product version source.

## Impact

This is an intentionally breaking release. Existing file workspaces remain
read-only inputs to the importer. Existing `/api/workspaces` and generic
knowledge endpoints are not part of the 0.3 public contract.
