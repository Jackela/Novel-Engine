/**
 * Client-side wall-clock watchdog for a proposal SSE stream (DR-026): it owns
 * the silence budget, the abort that releases a stalled connection, and the
 * diagnostics an abnormal ending reports.
 */

/** Bytes and delta frames observed before a stream ended abnormally. */
export interface StreamProgress {
  receivedBytes: number;
  deltaFrames: number;
}

/** `1 delta frame` versus `2 delta frames`, so diagnostics read as prose. */
function frameCountLabel(count: number): string {
  return count === 1 ? "1 delta frame" : `${count} delta frames`;
}

/** The diagnostic tail every abnormal ending names before it gives up. */
export function progressDetail(progress: StreamProgress): string {
  return `${frameCountLabel(progress.deltaFrames)}, ${progress.receivedBytes} bytes received.`;
}

/** Console tag for the anomaly lines a stalled or interrupted stream reports. */
const STREAM_ANOMALY_TAG = "[proposal-stream]";

/**
 * The browser console is the only sink a reader-side anomaly has: an
 * interrupted or stalled stream never reaches a server log line, so the
 * diagnostic has to stay on the client.
 */
export function reportStreamAnomaly(message: string, details: Record<string, unknown>): void {
  console.warn(STREAM_ANOMALY_TAG, message, details);
}

/** Raised (as the cause) when the watchdog aborted a stream that went silent. */
export class ProposalStreamStalledError extends Error {
  readonly code = "PROPOSAL_STREAM_STALLED";

  constructor(
    readonly silenceMs: number,
    readonly receivedBytes: number,
    readonly deltaFrames: number,
  ) {
    super(
      `No stream data arrived for ${Math.round(silenceMs / 1000)}s; ` +
        `${frameCountLabel(deltaFrames)}, ${receivedBytes} bytes received.`,
    );
    this.name = "ProposalStreamStalledError";
  }
}

export interface ProposalStreamWatchdog {
  /** Pass to `fetch`: aborting this releases the stalled connection's socket. */
  readonly signal: AbortSignal;
  /** (Re)start the silence budget; called before dispatch and after every chunk. */
  arm(): void;
  disarm(): void;
  /** The stall that aborted the stream, once the budget has elapsed. */
  stalled(): ProposalStreamStalledError | undefined;
  /** Detach the forwarded caller abort; called once this stream has ended. */
  dispose(): void;
}

/**
 * Build the deadline for one stream: silence with no bytes for `budgetMs`
 * aborts the connection and records the stall that caused it. `budgetMs <= 0`
 * disables the deadline, and the caller's own signal keeps aborting the request
 * exactly as it did before the watchdog existed.
 */
export function createProposalStreamWatchdog(
  budgetMs: number,
  callerSignal: AbortSignal | undefined,
  progress: StreamProgress,
): ProposalStreamWatchdog {
  const abort = new AbortController();
  const forwardAbort = (): void => abort.abort();
  callerSignal?.addEventListener("abort", forwardAbort, { once: true });
  if (callerSignal?.aborted === true) forwardAbort();
  let stall: ProposalStreamStalledError | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  return {
    signal: abort.signal,
    arm: () => {
      if (budgetMs <= 0) return;
      if (timer !== undefined) clearTimeout(timer);
      timer = setTimeout(() => {
        stall = new ProposalStreamStalledError(
          budgetMs,
          progress.receivedBytes,
          progress.deltaFrames,
        );
        abort.abort();
      }, budgetMs);
    },
    disarm: () => {
      if (timer !== undefined) clearTimeout(timer);
      timer = undefined;
    },
    stalled: () => stall,
    dispose: () => callerSignal?.removeEventListener("abort", forwardAbort),
  };
}
