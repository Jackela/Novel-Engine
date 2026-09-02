import type { TextGenerationStreamOptions } from "../../application/ports/text_generation.js";
import {
  discardHttpFailureResponse,
  isJsonObject,
  isResponseLike,
  malformedJsonFailure,
  type ProviderTransport,
  ProviderTransportError,
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
export const DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS = 30_000;
/** Ceiling on silence between consecutive stream frames. */
export const DEFAULT_STREAM_IDLE_TIMEOUT_MS = 60_000;

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
    return result;
  } catch (error) {
    pending.catch(() => undefined); // the raced read rejects only through teardown
    throw error;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

/**
 * Shared streaming engine for the HTTP adapters: dispatches the SSE request,
 * parses `data:` frames, extracts content deltas through the adapter's
 * extractor, and reports model plus final-chunk usage once the stream
 * completes. A stream is never retried — deltas already delivered cannot be
 * unsent — so the retry policy only guards the synchronous surface.
 */
export async function* streamProviderTextDeltas(
  request: StreamingTextRequest,
  transport: ProviderTransport,
  extractDelta: (chunk: JsonObject) => string | undefined,
  extractUsage: (chunk: JsonObject) => readonly [number | null, number | null],
  options?: TextGenerationStreamOptions,
): AsyncGenerator<string, void, void> {
  const deadline = startProviderResponseDeadline(
    request.context,
    request.timeoutSeconds,
    request.signal,
  );
  try {
    const response = await dispatchProviderResponse(
      transport,
      request.url,
      {
        method: "POST",
        headers: request.headers,
        body: request.body,
      },
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
    let promptTokens: number | null = null;
    let completionTokens: number | null = null;
    const frames = sseDataPayloads(body, { context: request.context, deadline });
    const iterator = frames[Symbol.asyncIterator]();
    let receivedFrame = false;
    try {
      while (true) {
        const budget = receivedFrame ? idleTimeoutMs(request) : firstByteTimeoutMs(request);
        const phase: SilencePhase = receivedFrame ? "idle" : "first-byte";
        deadline.assertActive();
        const step = await nextFrameWithin(iterator.next(), budget, phase, request, deadline);
        if (step.done === true) break;
        receivedFrame = true;
        const payload = step.value;
        if (payload.trim() === "[DONE]") break;
        const data = streamChunkObject(payload, request.context);
        const [prompt, completion] = extractUsage(data);
        if (prompt !== null) promptTokens = prompt;
        if (completion !== null) completionTokens = completion;
        const delta = extractDelta(data);
        if (delta !== undefined) yield delta;
      }
    } finally {
      try {
        await iterator.return?.();
      } catch {
        // Iterator cleanup cannot replace the first provider/application failure.
      }
    }
    deadline.assertActive();
    options?.onOutcome?.({ model: request.model, promptTokens, completionTokens });
  } finally {
    deadline.finish();
  }
}
