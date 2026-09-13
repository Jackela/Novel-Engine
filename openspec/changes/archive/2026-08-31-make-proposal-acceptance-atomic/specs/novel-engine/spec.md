## MODIFIED Requirements

### Requirement: Explicit AI proposals
AI operations MUST produce proposals persisted on jobs and MUST NOT mutate
documents until the author accepts the proposal. A proposal request MUST carry
`operation`, `instruction`, and `base_revision_id`, and its job result MUST
carry `proposal_markdown`, `base_revision_id`, and `accepted_revision_id`.
Acceptance MUST be limited to completed jobs with a non-empty proposal, MUST be
idempotent under repeated or concurrent requests, and MUST write the accepted
revision with source `ai-accepted` and `metadata.ai_job_id`. Creating and
indexing that revision, advancing the document and project, and binding the
job's `accepted_revision_id` MUST commit as one atomic operation.

#### Scenario: Generation leaves the manuscript untouched
- **GIVEN** a document currently points to revision A
- **WHEN** a proposal is generated from revision A and not accepted
- **THEN** the document still points to revision A
- **AND** no revision beyond A exists for that document

#### Scenario: Accept a completed proposal
- **GIVEN** a completed proposal job with non-empty proposal markdown
- **WHEN** the author accepts it
- **THEN** a new revision is created with source `ai-accepted`
- **AND** its metadata records `ai_job_id`
- **AND** the job result's `accepted_revision_id` names the new revision

#### Scenario: Invalid acceptance is rejected
- **GIVEN** a failed proposal job, or a completed one whose proposal markdown is empty
- **WHEN** the author attempts to accept it
- **THEN** the request is rejected under the unified error envelope
- **AND** no document revision is created

#### Scenario: Repeated acceptance is idempotent
- **GIVEN** a proposal job that was already accepted
- **WHEN** acceptance is requested again
- **THEN** the job is returned unchanged with the same `accepted_revision_id`
- **AND** exactly one accepted revision is created

#### Scenario: Concurrent acceptance is idempotent
- **GIVEN** two acceptance requests address the same completed proposal job
- **WHEN** they run concurrently
- **THEN** both converge on the same `accepted_revision_id`
- **AND** exactly one accepted revision is created

#### Scenario: Acceptance persistence failure rolls back every projection
- **GIVEN** a completed proposal whose acceptance begins from a current base revision
- **WHEN** any revision, document, project, FTS, or job-binding write fails
- **THEN** none of the acceptance writes commit
- **AND** the proposal remains safely retryable from the same base revision

#### Scenario: A legacy split acceptance repairs its job binding
- **GIVEN** an `ai-accepted` revision already records a proposal job's
  `metadata.ai_job_id` but that job has no `accepted_revision_id`
- **WHEN** acceptance is requested again
- **THEN** the job is bound to that existing revision
- **AND** no second revision is created
