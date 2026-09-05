import type { EventEmitter } from "node:events";

import type { ProposalStreamFrame } from "../../application/proposal_streaming.js";

/** SSE response headers: disable proxy buffering so deltas arrive immediately. */
const SSE_HEADERS = {
  "content-type": "text/event-stream; charset=utf-8",
  "cache-control": "no-cache",
  connection: "keep-alive",
  "x-accel-buffering": "no",
} as const;

const DEFAULT_DRAIN_TIMEOUT_MS = 30_000;

/** Stable internal diagnostic for a downstream response that never drains. */
export class ProposalStreamDrainTimeoutError extends Error {
  readonly code = "PROPOSAL_STREAM_DRAIN_TIMEOUT";

  constructor(timeoutMs = DEFAULT_DRAIN_TIMEOUT_MS) {
    super(`Proposal stream response did not drain within ${timeoutMs}ms.`);
    this.name = "ProposalStreamDrainTimeoutError";
  }
}

/** One SSE event: a single JSON frame per `data:` field, blank-line ended. */
function serializeFrame(frame: ProposalStreamFrame): string {
  return `data: ${JSON.stringify(frame)}\n\n`;
}

interface ProposalRawResponse extends EventEmitter {
  readonly writableFinished: boolean;
  writeHead(statusCode: number, headers: typeof SSE_HEADERS): unknown;
  write(chunk: string): boolean;
  end(): unknown;
  destroy(error?: Error): unknown;
}

export interface ProposalStreamResponseOptions {
  response: ProposalRawResponse;
  socket?: EventEmitter;
  frames: AsyncGenerator<ProposalStreamFrame, void, void>;
  disconnect: AbortController;
  hijack: () => void;
  pullFirst?: () => Promise<IteratorResult<ProposalStreamFrame, void>>;
  drainTimeoutMs?: number;
  /** Releases the app-local permit after every response and generator cleanup step. */
  releaseCapacity?: (() => void) | undefined;
}

type Interruption = { kind: "cancelled" } | { kind: "failure"; error: unknown };

interface ConnectionMonitor {
  interruption: () => Interruption | undefined;
  fail: (error: unknown) => void;
  subscribe: (listener: () => void) => () => void;
  dispose: () => void;
}

function monitorConnection(options: ProposalStreamResponseOptions): ConnectionMonitor {
  const { response, socket, disconnect } = options;
  let winner: Interruption | undefined;
  const subscribers = new Set<() => void>();
  const accept = (candidate: Interruption): void => {
    if (winner !== undefined) return;
    winner = candidate;
    if (!disconnect.signal.aborted) disconnect.abort();
    for (const subscriber of [...subscribers]) subscriber();
  };
  const cancel = (): void => accept({ kind: "cancelled" });
  const close = (): void => {
    if (!response.writableFinished) cancel();
  };
  const fail = (error: unknown): void => accept({ kind: "failure", error });

  disconnect.signal.addEventListener("abort", cancel);
  response.on("close", close);
  response.on("error", fail);
  socket?.on("close", close);
  if (disconnect.signal.aborted) cancel();

  return {
    interruption: () => winner,
    fail,
    subscribe: (listener) => {
      subscribers.add(listener);
      return () => subscribers.delete(listener);
    },
    dispose: () => {
      subscribers.clear();
      disconnect.signal.removeEventListener("abort", cancel);
      response.off("close", close);
      response.off("error", fail);
      socket?.off("close", close);
    },
  };
}

function waitForDrain(
  options: ProposalStreamResponseOptions,
  monitor: ConnectionMonitor,
): Promise<void> {
  const { response, drainTimeoutMs = DEFAULT_DRAIN_TIMEOUT_MS } = options;
  return new Promise((resolve, reject) => {
    let timer: ReturnType<typeof setTimeout>;
    let unsubscribe = (): void => {};
    let settled = false;
    const cleanup = (): void => {
      clearTimeout(timer);
      response.off("drain", onDrain);
      unsubscribe();
    };
    const settleFromInterruption = (): void => {
      if (settled) return;
      const interruption = monitor.interruption();
      if (interruption === undefined) return;
      settled = true;
      cleanup();
      if (interruption.kind === "failure") reject(interruption.error);
      else resolve();
    };
    const onDrain = (): void => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };
    const onTimeout = (): void => {
      if (settled) return;
      const failure = new ProposalStreamDrainTimeoutError(drainTimeoutMs);
      monitor.fail(failure);
      if (!response.writableFinished) response.destroy(failure);
    };
    response.once("drain", onDrain);
    unsubscribe = monitor.subscribe(settleFromInterruption);
    timer = setTimeout(onTimeout, drainTimeoutMs);
    settleFromInterruption();
  });
}

function continueOrThrow(monitor: ConnectionMonitor): boolean {
  const interruption = monitor.interruption();
  if (interruption?.kind === "failure") throw interruption.error;
  return interruption === undefined;
}

/** Write one proposal frame stream and release its generator exactly once. */
export async function writeProposalStreamResponse(
  options: ProposalStreamResponseOptions,
): Promise<void> {
  const { response, frames, hijack, pullFirst, releaseCapacity } = options;
  const monitor = monitorConnection(options);
  let streamFailure: unknown;
  try {
    if (continueOrThrow(monitor)) {
      let current = await (pullFirst?.() ?? frames.next());
      if (continueOrThrow(monitor)) {
        hijack();
        response.writeHead(200, SSE_HEADERS);
      }
      while (!current.done && continueOrThrow(monitor)) {
        const accepted = response.write(serializeFrame(current.value));
        if (!continueOrThrow(monitor)) break;
        if (!accepted) {
          await waitForDrain(options, monitor);
        }
        if (!continueOrThrow(monitor)) break;
        current = await frames.next();
      }
      if (continueOrThrow(monitor)) response.end();
    }
  } catch (error) {
    if (monitor.interruption() === undefined) monitor.fail(error);
    const interruption = monitor.interruption();
    if (interruption?.kind === "failure") streamFailure = interruption.error;
  }

  let cleanupFailure: unknown;
  try {
    await frames.return();
  } catch (error) {
    cleanupFailure = error;
  }

  const interruption = monitor.interruption();
  if (streamFailure === undefined && interruption?.kind === "failure") {
    streamFailure = interruption.error;
  }
  monitor.dispose();
  try {
    releaseCapacity?.();
  } catch (error) {
    cleanupFailure =
      cleanupFailure === undefined
        ? error
        : new AggregateError(
            [cleanupFailure, error],
            "Generator and capacity cleanup both failed.",
          );
  }

  if (streamFailure !== undefined && cleanupFailure !== undefined) {
    throw new AggregateError(
      [streamFailure, cleanupFailure],
      "Proposal stream and generator cleanup both failed.",
    );
  }
  if (streamFailure !== undefined) throw streamFailure;
  if (cleanupFailure !== undefined) throw cleanupFailure;
}
