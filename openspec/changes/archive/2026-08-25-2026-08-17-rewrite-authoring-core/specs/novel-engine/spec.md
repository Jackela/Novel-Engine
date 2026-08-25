## ADDED Requirements

### Requirement: SQLite authoring authority and immutable revisions
The system MUST persist projects, documents, and every accepted document
revision in SQLite as the single authoring authority, and every accepted
revision MUST be immutable once written. Creating a revision and advancing
the document to it MUST happen in one atomic operation. A save based on a
stale revision MUST be rejected through the conflict behavior defined by the
Unified error envelope Requirement instead of overwriting or merging any
revision.

#### Scenario: Conflict-checked save creates and advances atomically
- **GIVEN** a document currently points to revision A
- **WHEN** a client saves Markdown based on revision A
- **THEN** the system creates revision B with A as its parent revision
- **AND** the document points to revision B once the save returns
- **AND** revision A remains readable and unchanged

#### Scenario: Stale save is rejected through the error envelope
- **GIVEN** a document currently points to revision B
- **WHEN** a client saves Markdown based on revision A
- **THEN** the response is the 409 `REVISION_CONFLICT` defined by the Unified
  error envelope Requirement, with `details.current_revision_id` equal to
  revision B's identifier
- **AND** no revision is created, overwritten, or silently merged

### Requirement: Save request semantics
A document save MUST accept new content together with an optional new title
and metadata in the same request. Every accepted save MUST create a revision
numbered exactly one greater than the document's current revision number,
with the current revision as its parent, keeping numbering monotonic per
document. The revision source MUST be a server-assigned closed enum of
`author`, `ai-accepted`, and `restore`; the save request schema MUST NOT
expose a source field.

#### Scenario: Title and metadata change in the same save
- **GIVEN** a document points to revision A and is titled "Chapter 1"
- **WHEN** the author saves new content, a new title, and new metadata based
  on revision A
- **THEN** the created revision carries the new content
- **AND** the document's title and metadata reflect the same request
- **AND** the document advances to the new revision in one operation

#### Scenario: Revision numbering is monotonic with an unbroken chain
- **GIVEN** a document's latest revision is number 5
- **WHEN** two sequential saves based on the then-current revision succeed
- **THEN** the created revisions are numbered 6 and 7 in order
- **AND** each created revision's parent is the revision it was saved against

#### Scenario: Source is assigned by the server
- **GIVEN** a client attempts to supply a source value with a save
- **WHEN** the request is validated and executed
- **THEN** no client-supplied source is accepted
- **AND** the created revision's source is one of `author`, `ai-accepted`,
  or `restore`, as determined by the operation the server performed

### Requirement: Full-text search over current content
The system MUST expose project-scoped full-text search over document titles
and current content through a search endpoint, with the index synchronized
transactionally on every document create, save, and delete. Search input
MUST be reduced to safe tokens — case-folded word tokens, de-duplicated
preserving first occurrence, at most 8 tokens, combined with AND semantics —
and FTS5 operators, column filters, NEAR groups, wildcards, and punctuation
MUST NOT reach the match expression. Each result MUST identify the document
and carry its title and a plain-text excerpt of at most a 16-token window
around the best match, with truncation marked by an ellipsis and no highlight
markup. Results MUST be ordered by relevance rank, MUST NOT exceed 30 items,
and a query that reduces to no tokens MUST return an empty result list. All
full-text access MUST be centralized in a single search module, and index
writes and deletes MUST occur in the same transaction as the owning document
change.

#### Scenario: Ranked snippets for matching content
- **GIVEN** several documents of one project contain the word "lantern"
- **WHEN** the project search endpoint is called with `q=lantern`
- **THEN** matching documents are returned ordered by relevance rank
- **AND** each result carries the document identifier, title, and a
  plain-text excerpt
- **AND** no excerpt contains highlight markup such as `<mark>`

#### Scenario: Operator-laden input is safely reduced
- **GIVEN** a query stuffed with FTS5 syntax such as
  `dragon OR title:( NEAR(a b) wolf* ) "quotes"`
- **WHEN** the search runs
- **THEN** only the reduced quoted word tokens are matched with AND semantics
- **AND** no operator, column filter, NEAR group, or wildcard is executed as
  FTS5 syntax
- **AND** the response succeeds without error

#### Scenario: Unreducible input returns no results
- **GIVEN** a query that reduces to no word tokens, such as empty or
  punctuation-only input
- **WHEN** the search runs
- **THEN** the response succeeds with an empty result list
- **AND** no match expression is evaluated

#### Scenario: The index never serves stale content
- **GIVEN** a document matched an earlier search and is then deleted
- **WHEN** the same search runs again
- **THEN** the deleted document is absent from the results
- **AND** the deletion and its index cleanup committed in the same transaction

#### Scenario: Result count is bounded
- **GIVEN** more than 30 documents match the reduced tokens
- **WHEN** the search runs
- **THEN** at most 30 results are returned

### Requirement: Document identity and revision uniqueness
Document identity MUST be unique within a project by the triple (project,
kind, title); creating a duplicate MUST be rejected with an observable
conflict and MUST NOT create a second document. Revision numbers MUST be
unique per document, and each immutable snapshot MUST reference each
document at most once.

#### Scenario: Duplicate identity is rejected
- **GIVEN** a project already contains a chapter titled "Storm"
- **WHEN** a client creates another chapter titled "Storm" in that project
- **THEN** the API responds 409 with a stable conflict error under the
  unified error envelope
- **AND** the project still contains exactly one chapter titled "Storm"

#### Scenario: The same title is allowed under a different kind
- **GIVEN** a project already contains a chapter titled "Storm"
- **WHEN** a client creates a character document titled "Storm" in that
  project
- **THEN** the creation succeeds and both documents coexist

#### Scenario: Revision numbers never collide within a document
- **GIVEN** a document holds revisions numbered 1 through N
- **WHEN** any sequence of saves, restores, and accepted AI proposals creates
  further revisions
- **THEN** each new revision is numbered N+1 at creation time
- **AND** no two revisions of the document ever share a number

### Requirement: Stable list ordering
Every list endpoint MUST return a stable total order. The project list MUST
be ordered by `updated_at` descending, and a project's documents MUST be
ordered by kind, then position, then creation time. A reorder request naming
every document of the project exactly once MUST renumber positions 1..n in
the requested order; the partial-set rejection contract is defined by the
Request validation constraints Requirement.

#### Scenario: Most recently updated project first
- **GIVEN** project P1 was updated later than project P2
- **WHEN** the project list is requested
- **THEN** P1 appears before P2

#### Scenario: Documents sort by kind, position, then creation time
- **GIVEN** a project holds documents of several kinds with interleaved
  positions and creation times
- **WHEN** the project's documents are listed
- **THEN** they are ordered by kind first, then position, then creation time

#### Scenario: Full-set reorder renumbers positions
- **GIVEN** a project's documents A, B, C hold positions 1, 2, 3
- **WHEN** a reorder request lists C, A, B
- **THEN** C, A, B receive positions 1, 2, 3 respectively
- **AND** the response returns the documents in the requested order

### Requirement: Durable single-file operation
The system MUST keep authoring data durable in a single self-hosted database
file: every accepted write MUST remain intact after an abrupt process stop,
and referential integrity MUST hold after every operation, with dependent
rows removed by cascade and no orphaned rows appearing. At startup, when a
non-empty database file exists, the system MUST write a consistent backup
under `data/backups/` before applying any schema migration, and MUST skip
the backup when the database is absent or empty. Backups MUST NOT be removed
by the system itself.

#### Scenario: Data survives an abrupt restart
- **GIVEN** the server accepted saves and is then killed without a clean
  shutdown
- **WHEN** the server restarts
- **THEN** every accepted save is present and readable
- **AND** the database serves requests without repair actions

#### Scenario: Startup backs up before migrating
- **GIVEN** a non-empty database from an earlier release exists
- **WHEN** the server starts
- **THEN** a consistent backup capturing the pre-migration state exists
  under `data/backups/`
- **AND** schema migrations run only after that backup exists

#### Scenario: Referential integrity holds through cascades
- **GIVEN** a project with documents, revisions, and dependent workflow rows
- **WHEN** the project is deleted
- **THEN** its dependent rows are removed by cascade
- **AND** no orphaned rows remain

#### Scenario: Fresh database skips the backup
- **GIVEN** no database file exists
- **WHEN** the server starts for the first time
- **THEN** startup succeeds without writing a backup

### Requirement: Restart recovery without invented leases
On startup, every job left in the running state by a previous process MUST
be marked interrupted, MUST carry the fixed restart error, and MUST record a
job event naming the restart reason; the author MAY then explicitly retry
such a job. The system MUST NOT introduce lease columns, leases with TTLs,
heartbeats, lease renewal, worker registration, or any background executor
to implement this recovery: "lease" exists only as narrative wording inside
payload-visible strings, and jobs execute within the request lifecycle.

#### Scenario: Running job is interrupted at restart
- **GIVEN** a job is running when its process stops
- **WHEN** the next startup completes
- **THEN** the job reads as interrupted and carries the fixed restart error
- **AND** a job event records the restart reason
- **AND** the author can explicitly retry the job

#### Scenario: Recovery uses no lease machinery
- **GIVEN** the process stops at any point
- **WHEN** the next startup restores a consistent state
- **THEN** recovery performs only startup-time row updates and event inserts
- **AND** no lease, heartbeat, renewal, or worker-registration mechanism
  participates

### Requirement: Startup schema migration
Schema changes MUST ship as migration files that form the single deployment
source of truth — including full-text index DDL — and MUST be applied
programmatically at startup, after the safety backup and before the server
accepts traffic. Ad-hoc schema-push tooling MUST NOT be used against any
retained database.

#### Scenario: Upgrade first boot preserves data
- **GIVEN** a database created by an earlier release
- **WHEN** the new release starts for the first time
- **THEN** startup applies the pending migrations and succeeds
- **AND** the pre-existing projects, documents, and revisions remain intact

#### Scenario: Schema is never pushed to a retained database
- **GIVEN** a database holds live authoring data
- **WHEN** its schema needs to change
- **THEN** the change ships as a migration file applied at startup
- **AND** no direct schema-push path alters the retained database
