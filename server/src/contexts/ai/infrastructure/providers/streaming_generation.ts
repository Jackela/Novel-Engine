import {
  discardHttpFailureResponse,
  isJsonObject,
  isResponseLike,
  malformedJsonFailure,
  type ProviderRetryPolicy,
  type ProviderStreamOptions,
  type ProviderTransport,
  ProviderTransportError,
  runWithRetryPolicy,
} from "./provider_http.js";
import {
  dispatchProviderResponse,
  type ProviderResponseDeadline,
  startProviderResponseDeadline,
} from "./provider_response_lifecycle.js";
import { sseDataPayloads } from "./sseDataPayloads.js";

export { sseDataPayloads } from "./sseDataPayloads.js";

type JsonObject = Record<string, unknown>;

/** Ceiling on silence before the upstream sends its first stream byte. */
const DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS = 30_000;
/** Ceiling on silence between consecutive stream frames. */
const DEFAULT_STREAM_IDLE_TIMEOUT_MS = 60_000;

/** One outbound SSE generation request; failed response bodies never cross this boundary. */
export interface StreamingTextRequest {
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body: string;
  readonly signal: AbortSignal | undefined;
  readonly context: string;
  readonly timeoutSeconds: number;
  readonly model: string;
  /** Override for the built-in silence ceiling before the first stream byte. */
  readonly firstByteTimeoutMs?: number | undefined;
  /** Override for the built-in silence ceiling between stream frames. */
  readonly idleTimeoutMs?: number | undefined;
  /**
   * DR-006: retry policy for the pre-first-frame open phase. Absent keeps the
   * engine single-attempt; the adapters pass the same policy the synchronous
   * path retries with, so a transient 429/5xx or first-byte timeout recovers
   * instead of failing the whole stream.
   */
  readonly retry?: ProviderRetryPolicy | undefined;
}

function streamChunkObject(payload: string, context: string): JsonObject {
  let parsed: unknown;
  try {
    parsed = JSON.parse(payload);
  } catch (error) {
    if (error instanceof SyntaxError) throw malformedJsonFailure(context);
    throw error;
  }
  if (!isJsonObject(parsed)) throw malformedJsonFailure(context);
  return parsed;
}

function firstByteTimeoutMs(request: StreamingTextRequest): number {
  return request.firstByteTimeoutMs ?? DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS;
}

function idleTimeoutMs(request: StreamingTextRequest): number {
  return request.idleTimeoutMs ?? DEFAULT_STREAM_IDLE_TIMEOUT_MS;
}

/** Which silence budget fired, so operators can tell the two apart. */
type SilencePhase = "first-byte" | "idle";

/**
 * Normalize an elapsed silence budget into a retryable transport timeout that
 * names the budget and its real duration (not the overall request timeout).
 */
function silenceTimeoutFailure(
  context: string,
  budgetMs: number,
  phase: SilencePhase,
): ProviderTransportError {
  const seconds = Math.round(budgetMs / 1000);
  const detail =
    phase === "first-byte"
      ? `first-byte timeout after ${seconds}s`
      : `idle timeout after ${seconds}s of silence`;
  return new ProviderTransportError(`${context}: ${detail}.`, { timedOut: true });
}

/**
 * Await one stream frame, but never longer than the given silence budget:
 * when it elapses the guard aborts the dispatch, the loser of the race is
 * torn down, and the wait rejects with a normalized transport timeout.
 * DR-026: a received frame re-arms the absolute deadline (silence budget, not wall time).
 */
async function nextFrameWithin(
  pending: Promise<IteratorResult<string>>,
  budgetMs: number,
  phase: SilencePhase,
  request: StreamingTextRequest,
  deadline: ProviderResponseDeadline,
): Promise<IteratorResult<string>> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const elapsed = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(deadline.interrupt(silenceTimeoutFailure(request.context, budgetMs, phase)));
    }, budgetMs);
  });
  try {
    deadline.assertActive();
    const result = await Promise.race([pending, elapsed, deadline.interrupted]);
    deadline.assertActive();
    deadline.rearm();
    return result;
  } catch (error) {
    pending.catch(() => undefined); // the raced read rejects only through teardown
    throw error;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

// Iterator cleanup must never replace the first provider/application failure.
async function closeFrames(frames: AsyncGenerator<string, void, void> | undefined): Promise<void> {
  await frames?.return().catch(() => undefined);
}

// DR-006: an attempt may only be abandoned before any frame reached the
// adapter's extractor — retrying after that would replay incremental unwrapper
// state and corrupt the prose. This pulls exactly one frame and returns it
// unprocessed, so the caller's extractor is still pristine on failure; the
// caller owns the deadline and frame iterator once this resolves.
async function openStreamAttempt(
  request: StreamingTextRequest,
  transport: ProviderTransport,
): Promise<{
  readonly deadline: ProviderResponseDeadline;
  readonly frames: AsyncGenerator<string, void, void>;
  readonly firstFrame: IteratorResult<string, void>;
  readonly diagnostics: { frames: number; bytes: number };
}> {
  const deadline = startProviderResponseDeadline(
    request.context,
    request.timeoutSeconds,
    request.signal,
  );
  let frames: AsyncGenerator<string, void, void> | undefined;
  const diagnostics = { frames: 0, bytes: 0 };
  try {
    const response = await dispatchProviderResponse(
      transport,
      request.url,
      { method: "POST", headers: request.headers, body: request.body },
      request.context,
      deadline,
    );
    if (!isResponseLike(response)) {
      throw new ProviderTransportError(`${request.context}: transport returned no response`);
    }
    if (!response.ok) {
      throw await discardHttpFailureResponse(request.context, response, deadline.interrupt);
    }
    const body = response.body;
    if (body === null) {
      throw new ProviderTransportError(`${request.context}: transport returned no stream body`);
    }
    frames = sseDataPayloads(body, {
      context: request.context,
      deadline,
      onBytesReceived: (bytes) => {
        diagnostics.bytes += bytes;
      },
    });
    const firstFrame = await nextFrameWithin(
      frames.next(),
      firstByteTimeoutMs(request),
      "first-byte",
      request,
      deadline,
    );
    return { deadline, frames, firstFrame, diagnostics };
  } catch (error) {
    await closeFrames(frames);
    deadline.finish();
    throw error;
  }
}

/**
 * Shared streaming engine for the HTTP adapters: dispatches the SSE request,
 * parses `data:` frames, and reports model plus final-chunk usage once the
 * stream completes. DR-006: a transient pre-first-frame failure is retried
 * through the adapter's policy; after the first frame reached the extractor a
 * stream is never retried — a replay would corrupt the incremental unwrapper.
 * DR-026: the adapter's `extractStreamFailure` hook raises provider failure frames.
 * EOF without explicit protocol completion is a non-retryable provider failure.
 */
export async function* streamProviderTextDeltas(
  request: StreamingTextRequest,
  transport: ProviderTransport,
  extractDelta: (chunk: JsonObject) => string | undefined,
  extractUsage: (chunk: JsonObject) => readonly [number | null, number | null],
  options?: ProviderStreamOptions,
): AsyncGenerator<string, void, void> {
  const open = () => openStreamAttempt(request, transport);
  const { deadline, frames, firstFrame, diagnostics } =
    request.retry === undefined ? await open() : await runWithRetryPolicy(request.retry, open);
  let promptTokens: number | null = null;
  let completionTokens: number | null = null;
  let step = firstFrame;
  let terminalSeen = false;
  try {
    while (step.done !== true) {
      const payload = step.value;
      diagnostics.frames += 1;
      if (payload.trim() === "[DONE]") {
        terminalSeen = true;
        break;
      }
      const data = streamChunkObject(payload, request.context);
      const failure = options?.extractStreamFailure?.(data);
      if (failure !== undefined) throw failure;
      if (options?.isTerminalChunk?.(data) === true) terminalSeen = true;
      const [prompt, completion] = extractUsage(data);
      if (prompt !== null) promptTokens = prompt;
      if (completion !== null) completionTokens = completion;
      const delta = extractDelta(data);
      if (delta !== undefined) yield delta;
      deadline.assertActive();
      step = await nextFrameWithin(
        frames.next(),
        idleTimeoutMs(request),
        "idle",
        request,
        deadline,
      );
    }
    deadline.assertActive();
    if (!terminalSeen) {
      throw deadline.interrupt(
        new ProviderTransportError(
          `${request.context}: stream ended without a terminal frame (frames=${diagnostics.frames}, bytes=${diagnostics.bytes}).`,
        ),
      );
    }
  } finally {
    await closeFrames(frames);
    deadline.finish();
  }
  deadline.assertActive();
  options?.onOutcome?.({ model: request.model, promptTokens, completionTokens });
}
