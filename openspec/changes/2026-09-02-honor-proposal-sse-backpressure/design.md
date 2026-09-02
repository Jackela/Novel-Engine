# Design: pull-aware proposal response writer

## Connection monitor

A focused interface-layer module owns the raw response lifecycle. It observes
response errors, premature response or socket close, and a request-cancellation
signal behind one first-cause latch. A response error records the exact error
object before aborting upstream; a premature close records normal client
cancellation. Node's normal `finish` followed by `close` is not a disconnect:
once `writableFinished` records successful response completion, later close
events are ignored. Later events are no-ops and cannot overwrite the winner.

Long-lived connection listeners remain installed until generator cleanup has
finished. Removing them earlier would create an unobserved window while
`frames.return()` is still disposing Provider resources. Disposal is
idempotent and removes the exact references that were registered.

## Pull and drain protocol

One frame is serialized and passed to `write()` exactly once. A `true` result
allows the writer to request the next generator item. A `false` result means
that frame has already entered Node's buffer; the writer does not retry it and
does not call `frames.next()` again until `drain` wins the connection race.

Each drain wait also owns a 30-second no-progress timer. It installs only its
own `drain`, cancellation, and timer resources and removes them before
settling. If request cancellation, premature close, response error, or the
deadline wins, a later `drain` cannot resume pulling. The deadline is an
interface-owned fixed safety policy with an injected test seam; it does not
reuse or reset the Provider transport deadline. The writer checks interruption
before hijacking the response, after each write, after each drain wait, before
the next pull, and before ending the response.

The timer produces an internal `ProposalStreamDrainTimeoutError` with stable
diagnostic code `PROPOSAL_STREAM_DRAIN_TIMEOUT`. It is a downstream transport
failure, not an SSE error frame: once a backpressured response is hijacked, the
route aborts unfinished generation and destroys the still-open response rather
than trying to enqueue another frame. “First cause” below means the first event
observable by this writer; a Provider deadline that fires while the generator
is suspended at a yield is observed under the existing generator contract on
the next pull, not through a nonexistent reverse cancellation channel.

The existing application generator already pauses at every yielded delta, so
withholding its next pull also withholds the next Provider-stream read. No new
queue or application-layer buffering is introduced.

## Failure and cleanup ownership

The route captures the primary stream or connection failure, aborts upstream,
awaits `frames.return()` exactly once, and only then disposes the monitor. A
response error remains the primary exact object. If generator cleanup also
fails, the established primary-first `AggregateError` ordering is preserved;
normal disconnect is not promoted into a server error, although a cleanup
failure remains visible. A drain-deadline failure is visible as the primary
server-side transport failure and the unfinished raw response is closed.

Disconnect before the generator produces its terminal outcome keeps the
current no-job/no-usage behavior. Once the generator has durably landed a job
and produced a terminal frame, a later transport failure cannot roll that
outcome back; this change does not pretend that response delivery is part of
the database transaction.

The frontend cannot distinguish those two persistence states when cancellation
or transport failure hides a terminal done or error frame. Its callers enter
an explicit `outcome unknown` state and stop automatic whole-book continuation.
For the still-current project, they start a new, non-coalesced job-history read
after the client observes stream settlement and keep proposal/retry/resume
actions gated until it succeeds. A failed read remains unknown and offers audit
refresh retry only.

The refreshed history is audit evidence, not proof that any row belongs to the
interrupted attempt or that the server-side stream is quiescent. Browser abort
may settle before the server observes disconnect, so the snapshot may omit a
job that lands later and the outcome remains unknown after refresh. The UI says
the prior attempt may have landed, labels the next author action as generating
another proposal, and never auto-accepts an unobserved job. That explicit new
attempt may create another auditable job and usage event. Safe replay, unique
attempt matching, and a server completion barrier need a separate attempt-id
or idempotency contract and remain outside this transport change.

## Options rejected

- Continuing to write while `write()` returns false violates Node's writable
  contract and permits remotely driven memory growth.
- Retrying the same frame after `drain` would duplicate content because a
  false return still means the frame was accepted into the buffer.
- Treating every abort as a generic `AbortError` would hide an exact response
  failure and weaken first-cause diagnostics.
- Reusing the Provider deadline would couple two different clocks and still
  would not wake a route paused between generator pulls. A dedicated drain
  deadline bounds the interface resource that this writer owns.
