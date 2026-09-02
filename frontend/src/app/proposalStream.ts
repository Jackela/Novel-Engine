import { apiUrl, getCsrfToken, HttpError } from "@/app/api";
import { objectValue } from "@/app/apiContract";
import { parseJob } from "@/app/apiWorkflowContract";
import { localServiceUnavailable } from "@/app/networkError";
import type { StudioJob } from "@/app/types/studio";

/**
 * Streaming proposal client (#308): consumes the server's
 * `text/event-stream` with fetch + ReadableStream so credentials and the
 * CSRF header stay identical to the synchronous client. One terminal frame
 * resolves the stream — `done` carries the same job payload as the
 * synchronous endpoint, `error` rejects with the failed-job message.
 */

export class ProposalOutcomeUnknownError extends Error {
  readonly code = "PROPOSAL_OUTCOME_UNKNOWN";

  constructor(cause: unknown) {
    super(
      "The proposal stream ended before its final result was received. The outcome is unknown.",
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
    throw new Error(`Invalid proposal frame: not JSON (${data.slice(0, 64)})`);
  }
  const frame = objectValue(value, "proposal frame");
  const type = frame.type;
  if (type === "delta") {
    if (typeof frame.text !== "string") throw new Error("Invalid proposal frame: delta.text");
    return { type: "delta", text: frame.text };
  }
  if (type === "done") {
    if (typeof frame.job !== "object" || frame.job === null || Array.isArray(frame.job)) {
      throw new Error("Invalid proposal frame: done.job");
    }
    return frame as unknown as ProposalStreamFrame;
  }
  if (type === "error") {
    const error = objectValue(frame.error, "proposal frame.error");
    if (typeof error.code !== "string") throw new Error("Invalid proposal frame: error.code");
    if (typeof error.message !== "string") throw new Error("Invalid proposal frame: error.message");
    return {
      type: "error",
      error: { code: error.code, message: error.message },
    };
  }
  throw new Error(`Invalid proposal frame: unknown type (${String(type)})`);
}

function parseFrameEvent(rawEvent: string): ProposalStreamFrame {
  const data = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => (line.startsWith("data: ") ? line.slice(6) : line.slice(5)))
    .join("\n");
  if (data === "") throw new Error("Invalid proposal frame: missing data");
  return parseFramePayload(data);
}

async function readPreStreamError(response: Response): Promise<HttpError> {
  try {
    const payload = objectValue(await response.json(), "proposal error envelope");
    const error = objectValue(payload.error, "proposal error envelope.error");
    if (typeof error.code !== "string") {
      throw new Error("Invalid proposal error envelope: error.code");
    }
    if (typeof error.message !== "string") {
      throw new Error("Invalid proposal error envelope: error.message");
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
      frames.push(frame);
      if (frame.type === "done" || frame.type === "error") {
        this.buffer = "";
        this.terminal = true;
        return frames;
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
}: ProposalStreamRequest): Promise<StudioJob> {
  const path = `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;
  const csrfToken = getCsrfToken();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: JSON.stringify({ operation, instruction, provider }),
      signal,
    });
  } catch (error) {
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
    throw await readPreStreamError(response);
  }
  const body = response.body;
  if (body === null) {
    throw new ProposalOutcomeUnknownError(new HttpError("Proposal stream returned no body.", 502));
  }
  let reader: ReadableStreamDefaultReader<Uint8Array>;
  try {
    reader = body.getReader();
  } catch (error) {
    throw new ProposalOutcomeUnknownError(error);
  }
  const decoder = new TextDecoder();
  const parser = new ProposalStreamParser();
  let outcomeKnown = false;
  let reachedEof = false;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        reachedEof = true;
        break;
      }
      for (const frame of parser.append(decoder.decode(value, { stream: true }))) {
        if (frame.type === "delta") {
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
    const cause =
      (error instanceof Error || error instanceof DOMException) && error.name === "AbortError"
        ? new Error("Request cancelled.", { cause: error })
        : error;
    throw new ProposalOutcomeUnknownError(cause);
  } finally {
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
