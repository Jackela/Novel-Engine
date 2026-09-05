## ADDED Requirements

### Requirement: Authoring structure capacity

Each project's authoring structure MUST be bounded by fixed inclusive
limits: 2,500 documents per project, 100 volumes per project, 2,000
chapters per volume, 16,384 UTF-8 bytes of serialized Project settings
JSON, 16,384 UTF-8 bytes of serialized document metadata JSON, and 5,000
outline beats accepted by any single outline-document write. No request,
environment, or configuration input MAY relax these limits. Stored data
written before these limits MUST NOT be migrated, deleted, or rejected;
the limits gate only writes that would add new structure or grow a bounded
scalar.

A gated write that would exceed any limit MUST be refused before any
document row, revision, search-index entry, volume row, position update, or
project timestamp is written. The refusal MUST return 422
`STRUCTURE_CAPACITY_EXCEEDED` with message `Authoring structure capacity
exceeded.` and details containing only the closed `resource` name
(`project_documents`, `project_volumes`, `volume_chapters`,
`project_settings_bytes`, `document_metadata_bytes`, or `outline_beats`),
the inclusive numeric `limit`, and an `observed` value of at most
`limit + 1`. The refusal MUST be permanent for unchanged input and MUST
NOT carry a retry hint. Count limits MUST be checked inside the same
transaction that would perform the refused write, so two concurrent
creations cannot both pass one exhausted count. The outline-beat limit
MUST be enforced at every path that mints outline document content:
author saves, restores, and accepted AI proposals.

The OpenAPI contract for every route whose writes these limits gate MUST
document the 422 capacity envelope, and generated frontend API types MUST
remain synchronized with that contract.

#### Scenario: The 2,501st document is refused

- **GIVEN** a project already holds 2,500 documents
- **WHEN** the author creates one more document of any kind
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `project_documents`, `limit` 2,500, and `observed` 2,501
- **AND** the project still holds exactly 2,500 documents with unchanged
  order, revisions, and search index

#### Scenario: Creating at the exact document boundary succeeds

- **GIVEN** a project holds 2,499 documents
- **WHEN** the author creates one more document
- **THEN** the creation succeeds with the established 201 contract

#### Scenario: The 101st volume is refused

- **GIVEN** a project holds 100 volumes
- **WHEN** the author creates another volume
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `project_volumes`
- **AND** no volume row is written and reading order is unchanged

#### Scenario: Chapter placement into a full volume is refused

- **GIVEN** one volume already holds 2,000 chapters
- **WHEN** the author moves another chapter into that volume
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `volume_chapters`
- **AND** the chapter remains in its previous volume and position

#### Scenario: Volume deletion refuses an overflowing merge

- **GIVEN** deleting a volume would merge its chapters into the surviving
  neighbour and the merged count would exceed 2,000
- **WHEN** the author deletes that volume
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `volume_chapters`
- **AND** both volumes, their chapters, and all positions are unchanged

#### Scenario: Oversized settings JSON is refused

- **GIVEN** a project update carrying settings whose serialized UTF-8
  size exceeds 16,384 bytes
- **WHEN** the update is submitted
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `project_settings_bytes`
- **AND** the stored settings are unchanged
- **AND** an update at exactly 16,384 bytes succeeds

#### Scenario: Oversized document metadata is refused

- **GIVEN** a document save or create carrying metadata whose serialized
  UTF-8 size exceeds 16,384 bytes
- **WHEN** the write is submitted
- **THEN** the response is 422 `STRUCTURE_CAPACITY_EXCEEDED` with
  `resource` `document_metadata_bytes`
- **AND** no revision is created

#### Scenario: An outline write beyond the beat budget is refused

- **GIVEN** an outline document write whose markdown would hold more than
  5,000 beats, submitted as an author save, a revision restore, or an
  accepted AI proposal
- **WHEN** the write mints outline content
- **THEN** the response (or job outcome) is the 422
  `STRUCTURE_CAPACITY_EXCEEDED` refusal with `resource` `outline_beats`
- **AND** no revision is created and the outline's current content is
  unchanged
- **AND** an outline write at exactly 5,000 beats succeeds

#### Scenario: Existing over-limit data keeps reading

- **GIVEN** a project whose stored structures were written before these
  limits and already exceed one of them
- **WHEN** its shell, volumes, documents, exports, or whole-set reorders
  are read
- **THEN** no capacity error occurs
- **AND** only writes that would grow the saturated structure further are
  refused
