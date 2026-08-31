## MODIFIED Requirements

### Requirement: Snapshot-bound deterministic review
Every completed review MUST snapshot the project's current revisions (reason
`review`) with the fixed summary text, and its issues MUST be computed from the
source later persisted as that snapshot. Failed reviews MUST NOT persist a
review snapshot. For chapter documents: fewer than 250 words MUST produce
warning `thin_chapter` (message naming title and word count, the fixed
suggestion, evidence `{word_count}`); empty content MUST produce blocker
`empty_chapter`; both MAY fire on the same chapter. Non-chapter documents MUST
be skipped, and issues MUST be ordered by severity then code. Word counting
MUST use the one shared word definition wherever words are counted.

#### Scenario: Thin chapter is flagged
- **GIVEN** a chapter whose current revision has 249 words by the shared word-count definition
- **WHEN** a review runs
- **THEN** it reports warning `thin_chapter` for that chapter
- **AND** the evidence records `{"word_count": 249}`

#### Scenario: Empty chapter is a blocker and thin
- **GIVEN** a chapter whose current revision has empty content
- **WHEN** a review runs
- **THEN** it reports blocker `empty_chapter` and warning `thin_chapter` for that chapter

#### Scenario: Non-chapter documents are skipped
- **GIVEN** a project contains an outline document of ten words and one full chapter
- **WHEN** a review runs
- **THEN** no issue is reported for the outline document
- **AND** the chapter is evaluated

#### Scenario: Later edits do not rewrite review history
- **GIVEN** a completed review and a subsequent edit to a reviewed chapter
- **WHEN** the stored review is read
- **THEN** its issues still reflect the snapshotted revisions

#### Scenario: Upgrade removes only orphan review snapshots
- **GIVEN** an earlier release left a `review` snapshot with no assessment
- **WHEN** the database upgrades through the generated migration channel
- **THEN** that snapshot and its snapshot-document rows are removed
- **AND** completed-review and export snapshots remain intact

### Requirement: LLM editorial review
A review MUST read the project's current revisions as one ordered source and
MUST run the editorial review provider step over that source, producing
findings that each carry a severity (`blocker` or `warning`), a review
dimension from the server-owned closed dimension set, a message, and a
suggestion. Findings MUST be ordered by severity, then dimension, then document
position. A missing or non-array top-level `findings` value MUST be treated as
a provider contract failure; invalid individual findings MAY be discarded by
the closed vocabulary and source-document rules.

Before provider success, the system MUST NOT persist a review snapshot. On
fresh success, the `review` snapshot, snapshot documents, assessment, issues,
completed job, and completed event MUST commit atomically. On retry success,
the same review evidence and the running retry job's completed transition MUST
commit atomically, and the job MUST record the successful provider model. The
review stays snapshot-bound: later edits MUST NOT rewrite recorded findings. A
known provider failure or concurrently deleted source MUST produce a failed job
when the project still exists, MUST NOT fabricate findings, and MUST NOT leave
an unreferenced review snapshot.

#### Scenario: Dimensioned findings are reported
- **GIVEN** a captured source whose chapters contain pacing and continuity problems
- **WHEN** a review completes
- **THEN** each retained finding reports a dimension from the closed set with a severity, message, and suggestion
- **AND** the snapshot, assessment, issues, completed job, and event become visible together

#### Scenario: Provider failure fails the job
- **GIVEN** the editorial review provider step fails with a known provider error
- **WHEN** the review request completes
- **THEN** the job records status `failed` with the error
- **AND** no review snapshot, assessment, or finding is recorded

#### Scenario: Provider envelope is failure-closed
- **GIVEN** the provider returns a result whose top-level `findings` value is missing or is not an array
- **WHEN** the result is validated
- **THEN** the job records a provider contract failure
- **AND** no empty successful assessment or review snapshot is recorded

#### Scenario: Fresh completion rolls back as one outcome
- **GIVEN** a valid evaluated review
- **WHEN** any snapshot, assessment, issue, completed-job, or event write fails
- **THEN** none of those writes commit
- **AND** the source documents remain unblocked by review evidence

#### Scenario: Retry completion rolls back as one outcome
- **GIVEN** a running retry with a valid evaluated review
- **WHEN** its terminal transition fails
- **THEN** no new review snapshot, assessment, or issue commits
- **AND** the retry remains running for restart recovery

#### Scenario: Concurrent source deletion is failure-closed
- **GIVEN** a review source is read and one captured document is deleted before the result lands
- **WHEN** successful provider output is finalized
- **THEN** no partial review evidence commits
- **AND** the request records a failed review job if the project still exists

#### Scenario: Later edits do not rewrite review history
- **GIVEN** a review source is read and a captured chapter is subsequently edited
- **WHEN** the valid provider result lands
- **THEN** the completed review snapshot retains the originally captured revision
- **AND** later reads return the original snapshot-bound findings
