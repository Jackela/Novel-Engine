## MODIFIED Requirements

### Requirement: Synchronous job execution model

Proposal, review, export, and lore-extract jobs MUST execute synchronously
within their HTTP request, and the response MUST carry the job's terminal
state (`completed` or `failed`) — never an in-progress state requiring
polling. Jobs and job events MUST be persisted as an audit log; `running` is
an in-request transient, not a coordination primitive, and the system MUST
NOT add lease fields, heartbeats, or worker registration. At startup, jobs
left `running` MUST be marked `interrupted` with the fixed restart error
message and a matching job event.

Project job listings MUST return newest-first strict JobSummary items containing
only `id`, `project_id`, `document_id`, `kind`, `operation`, `status`,
`provider`, `model`, `error`, `retry_of_job_id`, `created_at`, and `updated_at`.
Summary items MUST NOT contain `request`, `result`, or `events`. Complete
proposal, review, export, lore-extract, retry, acceptance, and streamed
terminal responses MUST retain the complete Job payload. Project-scoped Job
detail MUST return that same complete payload with each event as
`{id, status, details, created_at}` in oldest-first order. Because the
frontend performs no polling, any move to asynchronous execution is a new
decision that MUST jointly reopen the frontend behavior contract.

In a JobSummary, `id`, `project_id`, `provider`, `model`, `created_at`, and
`updated_at` MUST be strings; `document_id`, `error`, and `retry_of_job_id`
MUST be string or null. `kind` MUST be one of `proposal`, `review`, `export`,
`lore-extract`, or `import`; `operation` MUST be one of `continue`,
`rewrite`, `generate`, `review`, `export`, `extract`, or `import`; and
`status` MUST be one of `pending`, `running`, `completed`, `failed`, or
`interrupted`. Timestamps MUST retain the existing ISO-8601 UTC string
serialization.

#### Scenario: One request reaches a terminal state

- **GIVEN** a proposal request
- **WHEN** the HTTP response is returned
- **THEN** the complete job it reports is `completed` or `failed`
- **AND** no client polling is required to learn the outcome

#### Scenario: Restart recovery

- **GIVEN** a job is `running` when the process exits
- **WHEN** the server starts again
- **THEN** the job is marked `interrupted` with the fixed restart error message and a matching job event
- **AND** the job becomes eligible for retry

#### Scenario: Events record every transition

- **GIVEN** one proposal that succeeds and one that fails
- **WHEN** their complete scoped Job details are requested
- **THEN** each carries its event stream with `{id, status, details, created_at}`
- **AND** events appear oldest first while the history list returns summaries only

#### Scenario: History returns strict summaries

- **GIVEN** persisted jobs contain large request, result, and event details
- **WHEN** their project history page is listed
- **THEN** each item contains exactly the twelve JobSummary fields
- **AND** request, result, and events are absent rather than null or optional

#### Scenario: One detail preserves the audit object

- **GIVEN** a persisted job has request, result, error, and transition events
- **WHEN** its scoped detail is requested
- **THEN** the complete values are returned without truncation
- **AND** its events appear oldest first

Complete failed Review and Export Jobs MAY carry `null` for their absent
`result.review_id` or `result.export_id`, respectively. The Studio MUST
recognize those terminal failures and expose their recorded error rather
than treating a null result ID as a malformed response. A null artifact ID
MUST be accepted only when its Job is failed and its kind corresponds to that
artifact. Completed Jobs and other Job kinds or states
MUST retain their existing rejection of null artifact IDs. Non-string,
non-null values for those result IDs MUST remain invalid.

#### Scenario: A known workflow failure has no result artifact

- **GIVEN** Review or Export execution records a failed complete Job with its corresponding result ID set to null
- **WHEN** the Studio receives its creation, detail, or retry response
- **THEN** it recognizes the failed Job and exposes the recorded operation error
- **AND** it does not claim that the response is unrecognizable solely because no result artifact exists

#### Scenario: Null artifact IDs remain invalid outside their failed workflow

- **GIVEN** a complete Job carries a null Review or Export result ID
- **WHEN** that Job is completed, another non-failed state, or a different kind from the corresponding artifact
- **THEN** the Studio rejects that field as a malformed response
- **AND** it does not present an artifact-less completed response as successful work
