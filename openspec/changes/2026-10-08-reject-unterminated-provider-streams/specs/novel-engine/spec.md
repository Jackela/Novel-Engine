## ADDED Requirements

### Requirement: Explicit HTTP Provider stream completion

An HTTP Provider stream MUST succeed only after a protocol-recognized completion signal. HTTP 200, received text, and EOF alone MUST NOT establish completion. EOF without completion MUST become a stable server-authored Provider failure, including when the stream is empty or contains only heartbeats.

For every supported HTTP Provider stream mode, `[DONE]` MUST retain its existing immediate completion behavior without waiting for EOF. Without `[DONE]`, compatible and native streams MUST require their protocol's legal completion `finish_reason` before EOF, and Responses streams MUST require `response.completed` with response status `completed`. A finish-reason signal MUST NOT stop consumption early: final usage and subsequent in-band errors MUST still be processed. Incomplete or failed Responses outcomes MUST NOT establish successful completion.

For an already-started Proposal API stream, unterminated Provider EOF MUST produce an `error` frame with code `PROVIDER_FAILED`, MUST NOT produce `done`, and MUST land a failed Job through the existing failure path. That path MUST preserve sanitized accumulated text as `partial_markdown` evidence and the existing zero-token `unreported` usage outcome. Partial text MUST NOT mutate the Document's Revision. The system MUST NOT automatically retry a stream after frames have escaped. Cancellation or the first established failure MUST remain authoritative during EOF handling and cleanup.

#### Scenario: Text followed by unterminated EOF

- **GIVEN** an HTTP Provider returns HTTP 200 and delivers text without a completion signal
- **WHEN** its stream reaches EOF
- **THEN** generation fails with a Provider failure
- **AND** an already-started Proposal API stream emits `PROVIDER_FAILED` without `done`
- **AND** a failed Job preserves sanitized `partial_markdown` and zero-token `unreported` usage
- **AND** the Document's Revision remains unchanged and no automatic retry occurs after escaped frames

#### Scenario: Empty or heartbeat-only EOF

- **GIVEN** an HTTP Provider returns HTTP 200 and sends no events or only heartbeat events
- **WHEN** its stream reaches EOF without a completion signal
- **THEN** the Provider stream fails rather than completing an empty Proposal

#### Scenario: Shared DONE signal

- **GIVEN** a supported HTTP Provider stream mode delivers `[DONE]`
- **WHEN** that signal is processed
- **THEN** explicit Provider completion is established immediately without requiring EOF

#### Scenario: Finish reason followed by final usage

- **GIVEN** a compatible or native Provider stream delivers its legal completion `finish_reason`
- **WHEN** final usage follows and then the stream reaches EOF
- **THEN** consumption includes the final usage and explicit completion is established

#### Scenario: In-band error after finish reason

- **GIVEN** a compatible or native Provider stream delivers its legal completion `finish_reason`
- **WHEN** an in-band Provider error follows before EOF
- **THEN** the error is processed and the stream fails instead of reporting completion

#### Scenario: Responses completion requires completed status

- **GIVEN** a Responses Provider stream delivers `response.completed` with response status `completed`
- **WHEN** the completion event is processed
- **THEN** explicit Provider completion is established
- **AND** a Responses stream ending without that event or the shared `[DONE]` marker cannot succeed

#### Scenario: Cancellation or first failure precedes EOF

- **GIVEN** cancellation or a Provider failure has already become authoritative
- **WHEN** stream termination or cleanup subsequently observes EOF without completion
- **THEN** EOF handling preserves the authoritative cancellation or failure
- **AND** cleanup does not replace it with a completion or a different failure
