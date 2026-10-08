## ADDED Requirements

### Requirement: Owner-operated ACP proxy
The product MUST provide an ACP proxy for the Owner's trusted clients through
the existing CLI. It MUST authenticate connections independently of Studio
cookies and MUST NOT present this service as multi-user process isolation.
The default listener MUST be loopback. A connecting CLI command MUST adapt
stdio clients to the custom WebSocket transport.

#### Scenario: Unauthenticated connection cannot launch an agent
- **GIVEN** a running ACP proxy and no valid bearer token
- **WHEN** a client attempts a WebSocket connection
- **THEN** the connection is refused before an agent process is launched

#### Scenario: Trusted client chooses a launch command
- **GIVEN** an authenticated Owner client
- **WHEN** its initialization supplies an executable, argument array and working directory
- **THEN** the proxy starts that command directly without a shell interpreter
- **AND** consumes its own launch extension before forwarding initialization

#### Scenario: Token remains outside the agent environment
- **GIVEN** a client authenticated with the proxy token
- **WHEN** the proxy starts its agent
- **THEN** the token is absent from the launch metadata forwarded to the agent and from the inherited agent environment
- **AND** the token is never placed in a URL or diagnostic output

#### Scenario: Stdio client uses the connecting command
- **GIVEN** a client that communicates only through stdio
- **WHEN** it launches the ACP connecting command with the proxy configuration
- **THEN** its requests, notifications and responses reach the selected agent
- **AND** stdout contains only protocol messages

### Requirement: Independently owned ACP connection lifecycle
Each proxy connection MUST own its launched process and protocol stream. The
proxy MUST bound message and pending-buffer sizes, reject invalid framing, and
clean up its process tree on disconnection or transport failure. Tool and
permission traffic MUST preserve its ACP meaning.

#### Scenario: Two clients do not share agent messages
- **GIVEN** two authenticated proxy connections
- **WHEN** their agents emit overlapping request identifiers
- **THEN** each message reaches only the connection that owns that agent

#### Scenario: Invalid or oversized framing closes the connection
- **GIVEN** an active proxy connection
- **WHEN** either side emits invalid JSON, unsupported framing or an oversized message
- **THEN** the proxy reports a bounded failure and closes the owned execution

#### Scenario: Disconnect cleans up execution
- **GIVEN** an agent and its child process are running
- **WHEN** the client disconnects
- **THEN** the owned process tree is stopped and transport listeners are released

### Requirement: Server-owned ACP Provider
The Studio MUST offer an ACP Provider for chapter draft, chapter revision,
editorial review and lore extraction. Its launch, model and materials workspace
MUST be configured by the server, never by a Studio generation request. Missing
configuration or failed authentication MUST fail explicitly without switching
to the trial Provider. The first supported agent MUST reuse the configured
local Grok CLI authentication without copying credentials into a container.

#### Scenario: Owner discovers the ACP Provider
- **GIVEN** an authenticated Owner
- **WHEN** provider discovery runs
- **THEN** ACP reports its configuration state and confirmed model, or null when model facts are not yet available
- **AND** it does not describe CLI configuration as a missing HTTP API key

#### Scenario: Studio cannot choose a process command
- **GIVEN** a Studio AI request
- **WHEN** the client supplies executable, arguments, working directory or model fields
- **THEN** request validation refuses those unsupported fields

#### Scenario: Four AI steps use the selected ACP agent
- **GIVEN** configured ACP and a supported AI step
- **WHEN** the step runs
- **THEN** it preserves the existing task language, output schema and business validation
- **AND** the result records the confirmed model and supported usage evidence

#### Scenario: Missing agent configuration does not use mock
- **GIVEN** ACP is selected but its connection or authentication is unavailable
- **WHEN** an AI step runs
- **THEN** it fails through the defined provider failure boundary
- **AND** no mock result is produced

### Requirement: ACP text completion and usage evidence
ACP text MUST pass the existing structured-output and chapter-delta contracts.
Thought, plan, tool and permission messages MUST NOT enter manuscript prose.
Successful completion MUST require complete protocol evidence. Missing usage
MUST remain unknown under existing provenance rules rather than inventing token
counts or billing amounts.

#### Scenario: Prose arrives incrementally
- **GIVEN** ACP streams a chapter JSON result in multiple escaped or Unicode chunks
- **WHEN** Studio observes the response
- **THEN** chapter prose arrives as real incremental deltas
- **AND** the completed content passes the existing schema and sanitization checks

#### Scenario: Tool or thought updates are separate
- **GIVEN** an agent emits prose alongside tool and thought updates
- **WHEN** Studio renders the Proposal
- **THEN** only the validated prose enters the Proposal text

#### Scenario: Interrupted completion is not success
- **GIVEN** the agent stops without a complete successful prompt outcome
- **WHEN** its connection closes or returns cancellation, refusal or exhaustion
- **THEN** no successful stream outcome or completed Proposal is invented
- **AND** existing partial evidence and manuscript authority are preserved

#### Scenario: Usage is absent
- **GIVEN** a successful agent response contains no trustworthy prompt or completion token evidence
- **WHEN** its usage is recorded
- **THEN** exact token fields remain absent and existing estimated or unreported provenance applies

### Requirement: Scoped agent observation and permission decisions
All four Studio AI steps MUST provide request-scoped progress observation and
an Owner permission decision surface. Decisions MUST be authenticated,
CSRF-protected, bound to the operation's project and active permission, and
limited to the options actually offered by the agent. Late, repeated or foreign
decisions MUST be refused. Waiting and disconnection MUST have finite cleanup.

#### Scenario: Permission can precede first prose
- **GIVEN** ACP asks permission before emitting chapter prose
- **WHEN** the Owner starts generation
- **THEN** the operation becomes observable before prose
- **AND** the Studio presents the pending action and offered decisions without a silent stream wait

#### Scenario: Review and Lore present the same permission behavior
- **GIVEN** a structured Review or Lore extraction requests a tool permission
- **WHEN** the operation is active
- **THEN** the Owner can observe and answer it while the final HTTP response remains pending

#### Scenario: Owner allows or refuses the offered action
- **GIVEN** an active permission with its original option identifiers
- **WHEN** the Owner submits one of those options
- **THEN** exactly that decision reaches the matching agent operation
- **AND** the UI does not misrepresent the scope of an always-allow option

#### Scenario: Expired or foreign permission is refused
- **GIVEN** a completed operation, a different project or a permission already answered
- **WHEN** a decision is submitted
- **THEN** it is rejected and no other operation receives it

#### Scenario: Navigation cancels its interaction
- **GIVEN** a project has active agent operations
- **WHEN** its Owner navigates away or the execution is cancelled
- **THEN** its subscriptions and pending permission waits are cleaned up
- **AND** late results cannot update the newly active project

### Requirement: Supporting-file tools preserve manuscript authority
The configured Novel Engine materials workspace MAY be read and written by
agent tools under the CLI's permissions. SQLite, secrets and registered immutable
export artifacts MUST remain outside this workspace. Tool effects MUST stay
distinct from accepted manuscript changes, and completed writes MUST NOT be
described as automatically reverted by cancellation or rejected generation.

#### Scenario: Tool updates a materials file
- **GIVEN** an allowed working file under the configured materials workspace
- **WHEN** the agent receives the required permission and writes it
- **THEN** the changed file is observable as a tool effect
- **AND** the Document Revision changes only through the existing save or Proposal acceptance operation

#### Scenario: Protected runtime file access is refused
- **GIVEN** a tool requests SQLite, secret configuration or a registered export original
- **WHEN** the Novel Engine file interface evaluates the target
- **THEN** it refuses the operation, including a symlink that resolves into the protected area

#### Scenario: Completed write survives cancellation
- **GIVEN** a permitted tool write has completed
- **WHEN** the Owner cancels subsequent generation
- **THEN** the Studio retains the completed-effect status
- **AND** it does not claim to restore the previous working file

### Requirement: Agent side effects prevent automatic prompt replay
After an agent prompt capable of side effects has been submitted, transport
failure MUST NOT automatically replay that prompt. Completed and uncertain tool
effects MUST be available for the Owner to assess before another execution.

#### Scenario: Connection fails after submission
- **GIVEN** a side-effect-capable prompt has been submitted
- **WHEN** the agent connection fails before a trustworthy outcome
- **THEN** the request fails without an automatic second prompt
- **AND** uncertain external effects are disclosed for inspection

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
MUST use the unified word-count definition wherever words are counted.
Editorial providers MUST receive the captured chapter text, chapter identity,
revision identity and reading order within the untrusted-manuscript boundary.
The complete prompt MUST respect the shared generation input budget and MUST
fail before provider execution when over budget; text MUST NOT be silently
truncated and presented as a complete manuscript review.

#### Scenario: Thin chapter is flagged
- **GIVEN** a chapter whose current revision has 249 words by the unified word-count definition
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

#### Scenario: Same counts do not hide different manuscripts
- **GIVEN** two captured chapters with equal titles and word counts but different text
- **WHEN** an editorial provider is invoked for each source
- **THEN** its manuscript input differs and identifies the corresponding revision

#### Scenario: Review captures text before provider waits
- **GIVEN** an editorial provider is awaiting completion
- **WHEN** the Owner edits or reorders chapters
- **THEN** the completed Review still references the originally captured text and reading order

#### Scenario: Over-budget review is refused
- **GIVEN** the complete captured Review prompt exceeds the shared input budget
- **WHEN** Review is requested
- **THEN** the operation reports the existing generation-capacity refusal without invoking a provider or persisting a successful snapshot
