## MODIFIED Requirements

### Requirement: Read-only idempotent legacy import

Import MUST never modify the source directory. A legacy workspace MUST contain
`story.yaml`; chapters come from immediate
`manuscript/chapters/chapter-*.md` files sorted by filename, and each becomes a
chapter document titled `Chapter N` by position, with no additional seeded
document. Import MUST be idempotent per owner scope: re-importing the same
accepted source hash within the owner scope returns the existing project
without duplication.

Web imports MUST be owner-only and confined to `data/imports`: path separators,
traversal, absolute paths, and symbolic links MUST be rejected. Every accepted
source file MUST be opened without following a final symbolic link, validated
as a regular file inside the captured workspace directories, and read through
that same fixed file identity. An observable workspace-directory or file-path
identity change during inspection MUST reject the complete workspace; no bytes
outside the captured workspace may enter its preview, hash, or imported content.

Inspection MUST accept at most 262,144 raw bytes for `story.yaml`, 4,194,304 raw
bytes for any chapter, 67,108,864 raw bytes across story and all accepted
chapters, 2,000 accepted chapters, and 4,096 observed entries in the chapter
directory. Exact limits are accepted. The next byte, chapter, or observed entry
MUST reject the complete workspace before UTF-8 decoding, preview output,
source-hash lookup, or database mutation. Inspection MUST be asynchronous and
MUST NOT synchronously load an unbounded directory or file on the HTTP event
loop. Capacity rejection MUST use HTTP 422 code `IMPORT_CAPACITY_EXCEEDED` with
bounded `resource`, `limit`, and `observed` details; CLI import MUST exit 1 for
the same failure and MUST NOT expose an unlimited override. Accepted workspaces
retain their existing hash, ordering, preview, and import semantics; files MUST
NOT be silently truncated or skipped.

#### Scenario: Repeated import is idempotent

- **GIVEN** a bounded legacy workspace was already imported by the owner
- **WHEN** the same accepted source is imported again
- **THEN** the existing project is returned
- **AND** no duplicate project is created

#### Scenario: Web sources are confined

- **GIVEN** a web preview source uses traversal, an absolute path, a symbolic link, or a path replaced during inspection
- **WHEN** the workspace is inspected
- **THEN** it is rejected before any outside bytes enter the preview or source hash
- **AND** no partial preview or database evidence is produced

#### Scenario: Legacy structure contract

- **GIVEN** a directory without `story.yaml`
- **WHEN** import is attempted
- **THEN** the request is rejected with an explicit error
- **AND** for a valid workspace, chapters are ordered by filename and titled `Chapter 1` through `Chapter N`

#### Scenario: Import budgets fail closed

- **GIVEN** any source file, accepted-file total, chapter count, or scanned-entry count is one unit above its fixed budget
- **WHEN** preview or import inspects the workspace
- **THEN** the complete operation is rejected before content decoding or store work
- **AND** the source remains unchanged and no partial project is created

#### Scenario: Exact import budgets remain compatible

- **GIVEN** a legacy workspace is exactly at every applicable byte and count budget
- **WHEN** preview or import inspects it
- **THEN** the workspace is accepted with its complete ordered content and stable source hash

### Requirement: CLI operational surface

The CLI MUST retain the `serve`, `import`, `backup`, and `doctor` commands. A
successful legacy import MUST print a bounded JSON summary containing project
id, title, description, import hash, chapter count, and a `created` boolean. The
summary MUST NOT contain imported document bodies and its size MUST NOT grow
with chapter Markdown. Re-importing the same accepted source MUST report
`created: false` and the existing project id.

#### Scenario: Serve backs up before migrating

- **GIVEN** the database authority and ambiguity gate passes for a database with pending migrations
- **WHEN** `serve` runs
- **THEN** a backup is written beneath the backups directory before migrations apply

#### Scenario: CLI import binds to an owner

- **GIVEN** a legacy workspace directory
- **WHEN** `import` runs with the explicit source path and owner name
- **THEN** the project is imported scoped to that owner without HTTP authentication
- **AND** the bounded imported-project summary is printed

#### Scenario: Doctor fails on corruption

- **GIVEN** a corrupted database
- **WHEN** `doctor` runs
- **THEN** the integrity check reports the corruption
- **AND** the exit code is non-zero

#### Scenario: CLI import output remains bounded

- **GIVEN** a valid legacy workspace with large chapter Markdown
- **WHEN** CLI import succeeds
- **THEN** it prints only the bounded import summary and exits 0
- **AND** a repeated import reports the same project id with `created: false`
