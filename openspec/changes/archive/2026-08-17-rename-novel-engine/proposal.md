# Rename the product label to Novel Engine

## Why

The product name is fragmented: the repository, package, and CLI are
`novel-engine`, while the spec, UI, and docs label the product "Novel
Studio". CONTEXT.md now defines Novel Engine as the canonical name, and the
legacy label is being removed outright rather than kept as an alias.

## What Changes

- Replace the label "Novel Studio" with "Novel Engine" across the capability
  spec, README, AGENTS.md, UI strings, CI workflow, issue templates, backend
  docstrings, settings defaults (`project_name`, API title), and the OpenAPI
  snapshot.
- Keep architecture identifiers unchanged: the `studio` bounded context,
  `Studio*` class names, and the `openspec/specs/novel-studio/` capability
  slug.

## Impact

Non-breaking. The OpenAPI snapshot changes because the API title and
description defaults change. No database, route, or payload changes.
