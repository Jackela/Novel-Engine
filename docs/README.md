# Documentation

This index routes readers to maintained guides and their source contracts.
Current code, package scripts, and workflows define implemented behavior;
the product specification defines requirements. A dated record establishes
evidence for its named commit, not the status of a later checkout.

## Use and operate Novel Engine

- [Project overview](../README.md): installation, configuration, CLI, and upgrades.
- [Quickstart](../openwiki/quickstart.md): cross-platform setup, first Owner
  session, local development, and validation prerequisites.
- [Studio workspace](../openwiki/frontend/studio-workspace.md): authoring,
  navigation, Inspector behavior, and responsive layouts.
- [Security policy](../.github/SECURITY.md) and [license](../LICENSE).
- [Changelog](../CHANGELOG.md): version history.

## Understand the product

- [Product specification](../openspec/specs/novel-engine/spec.md): canonical
  requirements; [active changes](../openspec/changes/) remain proposals until
  their workflow is complete.
- [Domain vocabulary](../CONTEXT.md) and [design notes](../DESIGN.md).
- [Architecture overview](../openwiki/architecture/overview.md): composition,
  persistence, providers, API contracts, and change guidance.
- Feature guides: [volumes and beats](../openwiki/architecture/volumes-and-beats.md),
  [resident context](../openwiki/architecture/resident-context.md),
  [lorebook](../openwiki/architecture/lorebook.md),
  [streaming and whole-book generation](../openwiki/architecture/streaming-and-whole-book.md),
  and [usage](../openwiki/architecture/usage.md).
- [Architecture decisions](adr/): dated rationale and constraints. Read later
  decisions and current implementation when assessing an older decision.

## Contribute and validate

- [Contribution guide](../CONTRIBUTING.md): Git workflow, tracking policy,
  documentation maintenance, and PR expectations.
- [Agent instructions](../AGENTS.md): repository engineering rules;
  [frontend instructions](../frontend/AGENTS.md) add frontend-specific rules.
- [CI gates](agents/ci-gates.md) and [change evidence](agents/change-evidence.md):
  checks, failure handling, candidate versions, and approval boundaries.
- [Issue tracker](agents/issue-tracker.md), [triage labels](agents/triage-labels.md),
  and [domain documentation](agents/domain.md): work and terminology ownership.
- [API error codes](agents/error-codes.md),
  [OpenAPI baseline](../server/qa-baselines/openapi.current.json), and
  [generated frontend types](../frontend/generated/api-types.ts): API references.
- [llms.txt](../llms.txt): machine-readable entry links to repository documents.

## Historical evidence and research

[Dated agent records](agents/), [audits](audits/), [research](research/), and
[archived OpenSpec changes](../openspec/changes/archive/) retain their original
scope and evidence. Research supports decisions; it does not override an
accepted product contract. Local passes, completed agent tasks, and old CI
results do not establish current release approval.

The retired Python implementation is preserved at Git tag `python-final`.
Use its historical reports only to understand that implementation; current
setup and validation belong to the TypeScript workspace guides above.
