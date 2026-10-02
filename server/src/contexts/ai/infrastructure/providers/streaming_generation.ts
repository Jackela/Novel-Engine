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
  boundedProviderBodyChunks,
  dispatchProviderResponse,
  MAX_PROVIDER_STREAM_EVENT_BYTES,
  type ProviderResponseDeadline,
  startProviderResponseDeadline,
  streamEventSizeFailure,
} from "./provider_response_lifecycle.js";

type JsonObject = Record<string, unknown>;

const MAX_BOUNDARY_PREFIX_BYTES = 3;

/** Ceiling on silence before the upstream sends its first stream byte. */
const DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS = 30_000;
/** Ceiling on silence between consecutive stream frames. */
const DEFAULT_STREAM_IDLE_TIMEOUT_MS = 60_000;

/** Strip exactly the one leading space the SSE `data:` field rule allows. */
function dataFieldValue(line: string): string {
  const value = line.slice("data:".length);
  return value.startsWith(" ") ? value.slice(1) : value;
}

function nextEventBoundary(
  buffer: string,
  fromIndex: number,
): { readonly index: number; readonly length: number } | undefined {
  let firstLf = buffer.indexOf("\n", fromIndex);
  while (firstLf >= 0) {
    const secondStart = firstLf + 1;
    const secondLength =
      buffer[secondStart] === "\n"
        ? 1
        : buffer[secondStart] === "\r" && buffer[secondStart + 1] === "\n"
          ? 2
          : 0;
    if (secondLength > 0) {
      const firstStart = buffer[firstLf - 1] === "\r" ? firstLf - 1 : firstLf;
      return { index: firstStart, length: firstLf + 1 + secondLength - firstStart };
    }
    firstLf = buffer.indexOf("\n", firstLf + 1);
  }
  return undefined;
}

/**
 * Parse an SSE body into `data:` payload strings: multi-line data fields join
 * with newlines, comments and other SSE fields are ignored, and a final
 * buffered event flushes even without a trailing blank line.
 */
export async function* sseDataPayloads(
  body: ReadableStream<Uint8Array>,
  options?: {
    readonly context: string;
    readonly deadline?: ProviderResponseDeadline | undefined;
  },
): AsyncGenerator<string, void, void> {
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  const context = options?.context ?? "Provider stream";
  const deadline = options?.deadline;
  let buffer = "";
  let bufferedBytes = 0;
  let boundaryScanIndex = 0;
  const assertEventSize = (rawEvent: string): void => {
    if (encoder.encode(rawEvent).byteLength <= MAX_PROVIDER_STREAM_EVENT_BYTES) return;
    const failure = streamEventSizeFailure(context);
    throw deadline?.interrupt(failure) ?? failure;
  };
  for await (const chunk of boundedProviderBodyChunks(body, context, deadline)) {
    buffer += decoder.decode(chunk, { stream: true });
    bufferedBytes += chunk.byteLength;
    let consumedCharacters = 0;
    let boundary = nextEventBoundary(buffer, boundaryScanIndex);
    while (boundary !== undefined) {
      const rawEvent = buffer.slice(consumedCharacters, boundary.index);
      assertEventSize(rawEvent);
      const payload = dataPayload(rawEvent);
      if (payload !== undefined) yield payload;
      consumedCharacters = boundary.index + boundary.length;
      boundary = nextEventBoundary(buffer, consumedCharacters);
    }
    if (consumedCharacters > 0) {
      buffer = buffer.slice(consumedCharacters);
      bufferedBytes = encoder.encode(buffer).byteLength;
    }
    boundaryScanIndex = Math.max(0, buffer.length - MAX_BOUNDARY_PREFIX_BYTES);
    if (bufferedBytes > MAX_PROVIDER_STREAM_EVENT_BYTES + MAX_BOUNDARY_PREFIX_BYTES) {
      const failure = streamEventSizeFailure(context);
      throw deadline?.interrupt(failure) ?? failure;
    }
  }
  buffer += decoder.decode();
  if (buffer.trim() !== "") {
    assertEventSize(buffer);
    const payload = dataPayload(buffer);
    if (payload !== undefined) yield payload;
  }
}

function dataPayload(rawEvent: string): string | undefined {
  const dataLines = rawEvent
    .split(/\r?\n/u)
    .filter((line) => line.startsWith("data:"))
    .map(dataFieldValue);
  return dataLines.length === 0 ? undefined : dataLines.join("\n");
}

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
}> {
  const deadline = startProviderResponseDeadline(
    request.context,
    request.timeoutSeconds,
    request.signal,
  );
  let frames: AsyncGenerator<string, void, void> | undefined;
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
    frames = sseDataPayloads(body, { context: request.context, deadline });
    const firstFrame = await nextFrameWithin(
      frames.next(),
      firstByteTimeoutMs(request),
      "first-byte",
      request,
      deadline,
    );
    return { deadline, frames, firstFrame };
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
 */
export async function* streamProviderTextDeltas(
  request: StreamingTextRequest,
  transport: ProviderTransport,
  extractDelta: (chunk: JsonObject) => string | undefined,
  extractUsage: (chunk: JsonObject) => readonly [number | null, number | null],
  options?: ProviderStreamOptions,
): AsyncGenerator<string, void, void> {
  const open = () => openStreamAttempt(request, transport);
  const { deadline, frames, firstFrame } =
    request.retry === undefined ? await open() : await runWithRetryPolicy(request.retry, open);
  let promptTokens: number | null = null;
  let completionTokens: number | null = null;
  let step = firstFrame;
  try {
    while (step.done !== true) {
      const payload = step.value;
      if (payload.trim() === "[DONE]") break;
      const data = streamChunkObject(payload, request.context);
      const failure = options?.extractStreamFailure?.(data);
      if (failure !== undefined) throw failure;
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
  } finally {
    await closeFrames(frames);
    deadline.finish();
  }
  deadline.assertActive();
  options?.onOutcome?.({ model: request.model, promptTokens, completionTokens });
}
