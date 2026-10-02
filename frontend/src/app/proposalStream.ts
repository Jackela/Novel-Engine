import { apiUrl, getCsrfToken, HttpError } from "@/app/api";
import { ApiContractError, objectValue } from "@/app/apiContract";
import { parseJob } from "@/app/apiWorkflowContract";
import { localServiceUnavailable } from "@/app/networkError";
import {
  createProposalStreamWatchdog,
  type ProposalStreamStalledError,
  progressDetail,
  reportStreamAnomaly,
  type StreamProgress,
} from "@/app/proposalStreamWatchdog";
import type { StudioJob } from "@/app/types/studio";

/**
 * Streaming proposal client (#308): consumes the server's
 * `text/event-stream` with fetch + ReadableStream so credentials and the
 * CSRF header stay identical to the synchronous client. One terminal frame
 * resolves the stream — `done` carries the same job payload as the
 * synchronous endpoint, `error` rejects with the failed-job message.
 */

/** Silence budget (ms) with no bytes at all before the client aborts the stream. */
const DEFAULT_STREAM_STALL_TIMEOUT_MS = 90_000;

export class ProposalOutcomeUnknownError extends Error {
  readonly code = "PROPOSAL_OUTCOME_UNKNOWN";

  constructor(cause: unknown, detail?: string) {
    super(
      "The proposal stream ended before its final result was received. The outcome is unknown." +
        (detail === undefined ? "" : ` ${detail}`),
      { cause },
    );
    this.name = "ProposalOutcomeUnknownError";
  }
}

export type ProposalStreamFrame =
  | { type: "delta"; text: string }
  | { type: "done"; job: StudioJob }
  | { type: "error"; error: { code: string; message: string } };

/** Runtime-validates one frame against the closed server frame contract. */
function parseFramePayload(data: string): ProposalStreamFrame {
  let value: unknown;
  try {
    value = JSON.parse(data);
  } catch {
    throw new ApiContractError(`proposal frame: not JSON (${data.slice(0, 64)})`);
  }
  const frame = objectValue(value, "proposal frame");
  const type = frame.type;
  if (type === "delta") {
    if (typeof frame.text !== "string") throw new ApiContractError("proposal frame: delta.text");
    return { type: "delta", text: frame.text };
  }
  if (type === "done") {
    if (typeof frame.job !== "object" || frame.job === null || Array.isArray(frame.job)) {
      throw new ApiContractError("proposal frame: done.job");
    }
    return frame as unknown as ProposalStreamFrame;
  }
  if (type === "error") {
    const error = objectValue(frame.error, "proposal frame.error");
    if (typeof error.code !== "string") throw new ApiContractError("proposal frame: error.code");
    if (typeof error.message !== "string")
      throw new ApiContractError("proposal frame: error.message");
    return {
      type: "error",
      error: { code: error.code, message: error.message },
    };
  }
  throw new ApiContractError(`proposal frame: unknown type (${String(type)})`);
}

/**
 * One SSE event as a frame, or `undefined` for a data-less event.
 * `: heartbeat` comments (and other events without a `data:` field) carry no
 * proposal frame; the server writes them to keep idle connections alive, so
 * they must never fail the stream.
 */
function parseFrameEvent(rawEvent: string): ProposalStreamFrame | undefined {
  const data = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => (line.startsWith("data: ") ? line.slice(6) : line.slice(5)))
    .join("\n");
  if (data === "") return undefined;
  return parseFramePayload(data);
}

async function readPreStreamError(response: Response): Promise<HttpError> {
  try {
    const payload = objectValue(await response.json(), "proposal error envelope");
    const error = objectValue(payload.error, "proposal error envelope.error");
    if (typeof error.code !== "string") {
      throw new ApiContractError("proposal error envelope: error.code");
    }
    if (typeof error.message !== "string") {
      throw new ApiContractError("proposal error envelope: error.message");
    }
    return new HttpError(error.message, response.status, error.details, error.code);
  } catch (error) {
    throw new ProposalOutcomeUnknownError(error);
  }
}

/**
 * Incremental parser for the SSE frame stream: feed it decoded text chunks,
 * it returns the complete frames. A trailing partial event stays buffered
 * until its terminating blank line arrives.
 */
export class ProposalStreamParser {
  private buffer = "";
  private terminal = false;

  append(chunk: string): ProposalStreamFrame[] {
    if (this.terminal) return [];
    this.buffer += chunk;
    const frames: ProposalStreamFrame[] = [];
    let boundary = this.buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const frame = parseFrameEvent(rawEvent);
      if (frame !== undefined) {
        frames.push(frame);
        if (frame.type === "done" || frame.type === "error") {
          this.buffer = "";
          this.terminal = true;
          return frames;
        }
      }
      boundary = this.buffer.indexOf("\n\n");
    }
    return frames;
  }
}

export interface ProposalStreamRequest {
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: "continue" | "rewrite" | "generate";
  readonly instruction: string;
  readonly provider: string;
  /** Aborting stops this client from observing the proposal; its server outcome may be unknown. */
  readonly signal?: AbortSignal;
  /** Invoked for every delta as the proposal markdown arrives. */
  readonly onDelta: (text: string) => void;
  /**
   * Wall-clock budget (ms) for the whole stream: silence with no bytes at all
   * for this long aborts the connection and reports the anomaly. Defaults to
   * `DEFAULT_STREAM_STALL_TIMEOUT_MS`; `0` disables the deadline.
   */
  readonly stallTimeoutMs?: number;
  /**
   * Durable idempotency key of this logical generation (DR-027): a resend that
   * carries the same key replays the server's existing job instead of drafting
   * — and billing — a second one. Optional; an absent key skips the header and
   * the server keeps its current behavior.
   */
  readonly idempotencyKey?: string;
}

/** Consume one streamed proposal; resolves with the terminal job payload. */
export async function streamProposal({
  projectId,
  documentId,
  operation,
  instruction,
  provider,
  signal,
  onDelta,
  stallTimeoutMs,
  idempotencyKey,
}: ProposalStreamRequest): Promise<StudioJob> {
  const path = `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;
  const csrfToken = getCsrfToken();
  const progress: StreamProgress = { receivedBytes: 0, deltaFrames: 0 };
  // The watchdog owns the request aborter: a stalled connection is torn down at
  // the socket instead of being held open by a client that has already given up.
  const watchdog = createProposalStreamWatchdog(
    stallTimeoutMs ?? DEFAULT_STREAM_STALL_TIMEOUT_MS,
    signal,
    progress,
  );
  const finishStream = (): void => {
    watchdog.disarm();
    watchdog.dispose();
  };
  /** The stall is a client-side anomaly: name it in the log and in the failure. */
  const stalledOutcome = (stalled: ProposalStreamStalledError): ProposalOutcomeUnknownError => {
    reportStreamAnomaly("stalled and was aborted", {
      silenceMs: stalled.silenceMs,
      deltaFrames: stalled.deltaFrames,
      receivedBytes: stalled.receivedBytes,
    });
    return new ProposalOutcomeUnknownError(stalled, stalled.message);
  };

  watchdog.arm();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
        ...(idempotencyKey === undefined ? {} : { "Idempotency-Key": idempotencyKey }),
      },
      body: JSON.stringify({ operation, instruction, provider }),
      signal: watchdog.signal,
    });
  } catch (error) {
    finishStream();
    const stall = watchdog.stalled();
    if (stall !== undefined) throw stalledOutcome(stall);
    let cause = error;
    if ((error instanceof Error || error instanceof DOMException) && error.name === "AbortError") {
      cause = new Error("Request cancelled.", { cause: error });
    }
    if (error instanceof TypeError) {
      cause = localServiceUnavailable(error);
    }
    throw new ProposalOutcomeUnknownError(cause);
  }
  if (!response.ok) {
    finishStream();
    throw await readPreStreamError(response);
  }
  const body = response.body;
  if (body === null) {
    finishStream();
    throw new ProposalOutcomeUnknownError(new HttpError("Proposal stream returned no body.", 502));
  }
  let reader: ReadableStreamDefaultReader<Uint8Array>;
  try {
    reader = body.getReader();
  } catch (error) {
    finishStream();
    throw new ProposalOutcomeUnknownError(error);
  }
  const decoder = new TextDecoder();
  const parser = new ProposalStreamParser();
  // The abort releases the request; cancelling the reader too keeps a
  // transport that ignores `signal` from leaving a read pending forever.
  const cancelOnAbort = (): void => {
    void reader.cancel().catch(() => undefined);
  };
  watchdog.signal.addEventListener("abort", cancelOnAbort, { once: true });
  if (watchdog.signal.aborted) cancelOnAbort();
  let outcomeKnown = false;
  let reachedEof = false;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        reachedEof = true;
        break;
      }
      watchdog.arm();
      progress.receivedBytes += value.byteLength;
      for (const frame of parser.append(decoder.decode(value, { stream: true }))) {
        if (frame.type === "delta") {
          progress.deltaFrames += 1;
          onDelta(frame.text);
        } else if (frame.type === "done") {
          const job = parseJob(frame.job);
          outcomeKnown = true;
          return job;
        } else {
          outcomeKnown = true;
          throw new HttpError(frame.error.message, 502, undefined, frame.error.code);
        }
      }
    }
    throw new HttpError("Proposal stream ended without a result.", 502);
  } catch (error) {
    if (outcomeKnown) throw error;
    if (signal?.aborted === true) {
      throw new ProposalOutcomeUnknownError(new Error("Request cancelled.", { cause: error }));
    }
    const stall = watchdog.stalled();
    if (stall !== undefined) throw stalledOutcome(stall);
    const cause =
      (error instanceof Error || error instanceof DOMException) && error.name === "AbortError"
        ? new Error("Request cancelled.", { cause: error })
        : error;
    // A malformed frame is a protocol defect, not a lost connection: only a
    // transport-level ending gets the interruption diagnostic.
    if (cause instanceof ApiContractError) throw new ProposalOutcomeUnknownError(cause);
    reportStreamAnomaly("interrupted before a terminal frame", { ...progress });
    throw new ProposalOutcomeUnknownError(cause, `Interrupted after ${progressDetail(progress)}`);
  } finally {
    finishStream();
    watchdog.signal.removeEventListener("abort", cancelOnAbort);
    if (!reachedEof) {
      try {
        await reader.cancel();
      } catch {
        // Terminal interpretation already owns the result; cleanup cannot change it.
      }
    }
    try {
      reader.releaseLock();
    } catch {
      // The reader is no longer reusable on any terminal path.
    }
  }
}
