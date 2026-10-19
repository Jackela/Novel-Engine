## MODIFIED Requirements

### Requirement: In-memory document drafts

An unsaved Draft—edited content, title, and save state—MUST live only in the
currently active editor's component memory. Leaving a Document MUST NOT retain
that Draft as client-side state for an inactive Document: it MUST NOT be
restored from inactive client memory or client-side storage across selection
changes, route departure, or page reload. A cached complete Document represents
only a server-accepted revision and MUST NOT store or be mutated into an
unsaved Draft.

A Draft that has not been accepted MUST NOT be dropped silently when its owner
is left. While an edited Draft has not been accepted, a deliberate selection of
another Document, or leaving the Studio surface with that Document open, MUST
hand the departing Document's newest local content and title to one rescue
write — one conflict-checked draft save addressed to that Document. The
departure MUST NOT duplicate a save attempt already in flight for that Document
with identical content and title, an unresolved conflict Draft MUST NOT enter
the rescue path, and the departing editor's local Draft is discarded once the
rescue write is issued. The rescue's result is observable only as an accepted
revision of its own Document: reopening that Document MUST read the rescued
text back from the server rather than from inactive client state, and MUST NOT
save it again. A rescue write that fails, conflicts, or never lands MUST remain
silent and MUST NOT claim acceptance; the next open reads the server state, and
the explicit save surface keeps ownership of user-visible save errors.

After 1.5 seconds without a newer edit, the Studio MUST start the existing
conflict-checked autosave attempt. The debounce bounds when an attempt starts;
it MUST NOT be presented as a guarantee that the Draft is durable, because a
request can fail, conflict, be cancelled, or lose its response. A 409 `REVISION_CONFLICT` MUST
retain the local Draft and a separate latest-server baseline while that
Document remains active. The active local Draft ends only by successful
acceptance, an explicit conflict choice that replaces it, a departure that
hands the newest text to its one rescue write, or a reload. A late save,
rescue, or conflict outcome MUST NOT publish into a newly active Document.

While the same selected Document still owns unaccepted Draft text or title,
the Studio MUST retain its unsaved-change close/refresh guard when the
accepted body is temporarily unavailable after an earlier save. A pending or
failed body reload MUST NOT be treated as proof that the Draft was saved.
The comparison MUST use the current owner's accepted text and title; returning
to that accepted content, explicitly discarding the Draft, or switching to a
clean owner MUST NOT leave a stale warning.

Automatic retries MUST NOT repeat an unchanged Draft after a permanent HTTP
413 or 422 save refusal. The active Draft and its visible error MUST remain
available for correction or an explicit retry. Editing that Draft MUST resume
the ordinary debounced save path. Transient transport failure retry and the
explicit `REVISION_CONFLICT` path MUST retain their existing behavior. A
409 `DOCUMENT_CONFLICT` MUST retain the Draft as an editable save error,
without presenting revision-conflict replacement actions or automatically
repeating the unchanged title.

#### Scenario: Switching documents discards the draft

- **GIVEN** the active Document has unsaved edits and no unresolved conflict Draft
- **WHEN** the author deliberately switches to another Document
- **THEN** exactly one save for the departing Document carries its newest local content and title as that Document's rescue write
- **AND** the departing editor's local Draft is discarded and no client-side Draft copy remains
- **AND** the next Document loads from its accepted current revision
- **AND** a late response for the earlier Document cannot replace the new editor state

#### Scenario: Leaving the Studio rescues the pending draft once

- **GIVEN** the author edits a Document and leaves the Studio before the 1.5-second debounce elapses
- **WHEN** the departure happens
- **THEN** exactly one rescue write for the departing Document carries its newest local content
- **AND** no write is issued for another Document or project
- **AND** waiting past the debounce window issues no duplicate late save

#### Scenario: A reopened document reads back the rescued text

- **GIVEN** a departure's rescue write was accepted as a revision of that Document
- **WHEN** the author opens that Document again
- **THEN** the editor shows the rescued content and title read back from the server, settled as saved
- **AND** re-entry issues no further save for that Document

#### Scenario: An unresolved conflict draft is not rescued

- **GIVEN** the active Document holds an unresolved conflict Draft
- **WHEN** the author deliberately switches to another Document
- **THEN** no rescue write is issued for the conflicted text
- **AND** the conflict Draft is discarded with the departure
- **AND** opening that Document again reads its last accepted revision

#### Scenario: A failed rescue write stays silent

- **GIVEN** a departure's rescue write fails or never lands
- **WHEN** the author opens that Document again
- **THEN** the editor shows that Document's last accepted revision
- **AND** no error, acceptance claim, or client-side Draft copy from the failed rescue is published

#### Scenario: No client-side draft persistence

- **GIVEN** unsaved edits
- **WHEN** the page reloads
- **THEN** the editor loads the last accepted current revision with no Draft recovery

#### Scenario: Debounce starts an attempt but does not claim durability

- **GIVEN** the author stops typing in an unsaved Draft
- **WHEN** 1.5 seconds elapse without a newer edit
- **THEN** the Studio starts a conflict-checked save attempt
- **BUT WHEN** that attempt fails, conflicts, or is cancelled
- **THEN** the product does not claim the Draft was accepted or durable

#### Scenario: Conflict retains the active local Draft

- **GIVEN** autosave receives a revision conflict while the same Document remains active
- **WHEN** the latest server Document is loaded as the conflict baseline
- **THEN** the local Draft remains separately available for the explicit conflict actions
- **AND** neither value silently overwrites the other

#### Scenario: A permanent size or validation refusal stops automatic retry

- **GIVEN** a save of the active Draft is refused with HTTP 413 or 422
- **WHEN** automatic retry intervals elapse without another edit
- **THEN** no further save request is sent for that unchanged Draft
- **AND** the local title, content, and readable save error remain available
- **WHEN** the author corrects the Draft
- **THEN** the ordinary debounced save may persist the corrected text

#### Scenario: A later local edit stays guarded during accepted-body reload

- **GIVEN** an autosave is in flight and the author makes a newer local edit
- **WHEN** the earlier save succeeds and the subsequent accepted-body read is pending or fails
- **THEN** the same owner's latest Draft remains protected by the unsaved-change close/refresh guard
- **AND** saved-source Review and Export guidance continues to identify unaccepted chapter edits
- **WHEN** the author restores the accepted content or explicitly discards the Draft
- **THEN** the stale warning is removed without retaining an inactive Draft


### Requirement: Provider transient failure handling
For synchronous structured generation calls, both HTTP providers MUST share
one retry policy with an identical retryable set: HTTP 429, 500, 502, 503,
504, transport timeout (including an absolute response deadline), and malformed
JSON responses are retried up to the configured limit (default three total
attempts, with one-second spacing between attempts); every other error fails
immediately without retry. Retry decisions MUST read structured error fields
(status code, timeout, retryability), never substring matches on
human-readable message text, and both HTTP providers MUST share the same retry
module. A retryable per-attempt deadline failure MUST NOT record the normal
failed proposal outcome until the attempt budget is exhausted. Synchronous
generation steps (`chapter_draft`, `chapter_revision`) MUST be granted a
timeout floor of 180 seconds. Any product-owned client or application-handler
timeout that remains active while Provider execution runs MUST NOT be shorter
than that floor; the earlier inbound request-receipt threshold is complete
before Provider execution and does not enclose it.

For synchronous DashScope Responses generation, a documented response status
of `failed`, `incomplete`, `cancelled`, `in_progress`, or `queued` MUST NOT be
recorded as completed generation, even when HTTP is 200 and output contains
parseable structured prose. These statuses MUST use the existing immediate,
non-retryable failure path, without creating an acceptable Proposal or exposing
untrusted Provider diagnostics. Handling of omitted status in existing
compatible responses MUST remain unchanged.

#### Scenario: Transient error is retried
- **GIVEN** the provider answers 429 once and then succeeds
- **WHEN** a proposal is requested
- **THEN** the job completes with a proposal
- **AND** the transient failure is not surfaced as a job error

#### Scenario: Persistent failure exhausts retries
- **GIVEN** the provider answers 503 on every attempt
- **WHEN** a proposal is requested
- **THEN** the job fails with the provider error after three total attempts by default

#### Scenario: Non-retryable failure is immediate
- **GIVEN** the provider answers 401
- **WHEN** a proposal is requested
- **THEN** the job fails after one attempt

#### Scenario: Generation timeout floor
- **GIVEN** a chapter revision generation on an HTTP provider
- **WHEN** the request is dispatched
- **THEN** the provider call is granted at least 180 seconds
- **AND** no product-owned client or application-handler timeout that remains
  active during Provider execution ends sooner

#### Scenario: Structured prose cannot override a non-completed response

- **GIVEN** a synchronous DashScope Responses payload has a documented non-completed status and otherwise valid Proposal prose
- **WHEN** the Provider adapter handles the HTTP 200 response
- **THEN** the Job fails after one Provider attempt and contains no acceptable Proposal
- **AND** accepting that Job cannot create a Revision or change the Document
- **AND** Provider-supplied error text is not copied into author-visible diagnostics

#### Scenario: Completed and legacy compatible responses remain usable

- **GIVEN** a synchronous Responses payload contains valid Proposal prose and status completed or no status field
- **WHEN** it is handled by the same adapter
- **THEN** the existing successful generation and explicit acceptance flow remains available


### Requirement: Bounded Studio review-history state

The Studio MUST initialize the Review panel from one bounded first summary
page when that panel is the URL-selected Inspector history, and inactive
panels MUST NOT prefetch or publish late outcomes. Older summaries MUST enter
only through an explicit accessible load-older action that appends unique
summaries without clearing the page; its failure MUST preserve committed
summaries and the saved cursor for retry. The newest summary MUST drive one
lazy detail read of the newest assessment's findings; an empty first page
MUST skip it. Completing a review run MUST refresh only the cursorless first
page and the newest detail, MUST NOT traverse older pages, and MUST NOT be
satisfied by a stale response. Project changes MUST abort in-flight review
reads and reject stale responses from publishing into another owner. Loading
older reviews MUST follow the History panel's keyboard focus rules: failure
restores the retryable control, terminal success moves focus to the panel
heading when focus has no connected owner, and a newer author-chosen focus
target is never overridden.

A completed Review Job retry MUST invalidate that project's cached Review
history and clear the preceding Review command error even if refreshing the
Jobs list subsequently fails. When Review is
inactive, invalidation MUST NOT prefetch; the next activation MUST read only
one cursorless first page and its newest detail, reset an earlier explicit
selection, and reject stale page/detail/older outcomes. Failed retries,
non-Review jobs, and late completions from a departed project MUST NOT clear
or replace the active project's Review history.

#### Scenario: Lazy activation reads only the selected history

- **GIVEN** the Inspector is on another tab
- **WHEN** review history has not been selected
- **THEN** no review request is made
- **BUT WHEN** the Review tab is selected
- **THEN** one cursorless first page and its newest detail are read

#### Scenario: Load older is explicit and recoverable

- **GIVEN** the Review panel shows a page and a non-null cursor
- **WHEN** the author activates Load older reviews
- **THEN** one cursor request appends unique older summaries without clearing
  the page
- **BUT WHEN** that request fails
- **THEN** existing summaries and the cursor remain available for retry

#### Scenario: Newest findings follow the detail read

- **GIVEN** the first page names review A as newest
- **WHEN** its findings are displayed
- **THEN** they come from review A's detail read rather than the list page
- **AND** a refreshed first page naming review B triggers review B's detail
  instead

#### Scenario: A completed run refreshes only the first page

- **GIVEN** the author has loaded older review summaries
- **WHEN** a review run completes
- **THEN** exactly one cursorless first-page refresh is issued
- **AND** no older page is traversed automatically
- **AND** a stale pre-run response cannot publish summaries or findings

#### Scenario: Project change rejects late review responses

- **GIVEN** a review page or detail request is in flight
- **WHEN** the author switches projects
- **THEN** the request is aborted or its outcome suppressed
- **AND** the new project's review state starts from its own first page

#### Scenario: Retried Review becomes visible on the next activation

- **GIVEN** Review A is cached and the author retries a failed Review from Jobs
- **WHEN** the retry completes with new Review B while Review is inactive
- **THEN** no inactive Review request is made
- **WHEN** the author returns to Review
- **THEN** one fresh first page and B's detail are read without walking older pages
- **AND** a previous selected Review or late old response cannot hide B

#### Scenario: Jobs refresh failure does not conceal a completed Review

- **GIVEN** a Review retry completed but the following Jobs refresh failed
- **WHEN** the author opens Review
- **THEN** Review still loads the completed retry's newest assessment through its own recovery surface

#### Scenario: Successful retry clears the preceding Review error

- **GIVEN** a failed Review command left a visible error
- **WHEN** its Review Job retry completes in the same project
- **THEN** the preceding Review error is cleared and the newest assessment is loaded on activation
- **AND** failed, non-Review, or departed-project retry outcomes do not clear that error
