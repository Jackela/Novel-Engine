import type { TextGenerationStreamOptions } from "../../application/ports/text_generation.js";
import {
  classifyTransportRejection,
  httpStatusFailure,
  malformedJsonFailure,
  type ProviderTransport,
  ProviderTransportError,
  redactCredentialAndTruncateResponseBody,
  timeoutFailure,
} from "./provider_http.js";

type JsonObject = Record<string, unknown>;

const EVENT_BOUNDARY = /\r?\n\r?\n/u;

/** Ceiling on silence before the upstream sends its first stream byte. */
export const DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS = 30_000;
/** Ceiling on silence between consecutive stream frames. */
export const DEFAULT_STREAM_IDLE_TIMEOUT_MS = 60_000;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isResponseLike(value: unknown): value is Response {
  if (!isJsonObject(value)) return false;
  return (
    typeof value.ok === "boolean" &&
    typeof value.status === "number" &&
    typeof value.text === "function" &&
    typeof value.json === "function"
  );
}

function readableResponse(response: Response): Response {
  return typeof response.clone === "function" ? response.clone() : response;
}

/** Strip exactly the one leading space the SSE `data:` field rule allows. */
function dataFieldValue(line: string): string {
  const value = line.slice("data:".length);
  return value.startsWith(" ") ? value.slice(1) : value;
}

/**
 * Parse an SSE body into `data:` payload strings: multi-line data fields join
 * with newlines, comments and other SSE fields are ignored, and a final
 * buffered event flushes even without a trailing blank line.
 */
export async function* sseDataPayloads(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<string, void, void> {
  const decoder = new TextDecoder();
  let buffer = "";
  for await (const chunk of body) {
    buffer += decoder.decode(chunk, { stream: true });
    let boundary = EVENT_BOUNDARY.exec(buffer);
    while (boundary !== null) {
      const rawEvent = buffer.slice(0, boundary.index);
      buffer = buffer.slice(boundary.index + boundary[0].length);
      const payload = dataPayload(rawEvent);
      if (payload !== undefined) yield payload;
      boundary = EVENT_BOUNDARY.exec(buffer);
    }
  }
  buffer += decoder.decode();
  if (buffer.trim() !== "") {
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

/** One outbound SSE generation request; credential redaction stays adapter-side. */
export interface StreamingTextRequest {
  readonly url: string;
  readonly headers: Record<string, string>;
  readonly body: string;
  readonly signal: AbortSignal | undefined;
  readonly context: string;
  readonly timeoutSeconds: number;
  readonly credential: string;
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

function dispatchSignal(request: StreamingTextRequest, guard: AbortController): AbortSignal {
  return request.signal === undefined
    ? guard.signal
    : AbortSignal.any([request.signal, guard.signal]);
}

/**
 * Await one stream frame, but never longer than the given silence budget:
 * when it elapses the guard aborts the dispatch, the loser of the race is
 * torn down, and the wait rejects with a normalized transport timeout.
 */
async function nextFrameWithin(
  pending: Promise<IteratorResult<string>>,
  budgetMs: number,
  request: StreamingTextRequest,
  guard: AbortController,
): Promise<IteratorResult<string>> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const elapsed = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      guard.abort();
      reject(timeoutFailure(request.context, request.timeoutSeconds));
    }, budgetMs);
  });
  try {
    return await Promise.race([pending, elapsed]);
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
  let response: Response | undefined;
  const guard = new AbortController();
  try {
    response = await transport(request.url, {
      method: "POST",
      headers: request.headers,
      body: request.body,
      signal: dispatchSignal(request, guard),
    });
  } catch (error) {
    throw classifyTransportRejection(error, request.context, request.timeoutSeconds);
  }
  if (!isResponseLike(response)) {
    throw new ProviderTransportError(`${request.context}: transport returned no response`);
  }
  if (!response.ok) {
    const responseBody = await readableResponse(response).text();
    throw httpStatusFailure(
      request.context,
      response.status,
      redactCredentialAndTruncateResponseBody(responseBody, request.credential),
    );
  }
  const body = response.body;
  if (body === null) {
    throw new ProviderTransportError(`${request.context}: transport returned no stream body`);
  }
  let promptTokens: number | null = null;
  let completionTokens: number | null = null;
  const frames = sseDataPayloads(body);
  const iterator = frames[Symbol.asyncIterator]();
  let receivedFrame = false;
  try {
    while (true) {
      const budget = receivedFrame ? idleTimeoutMs(request) : firstByteTimeoutMs(request);
      const step = await nextFrameWithin(iterator.next(), budget, request, guard);
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
    // Best-effort teardown: a stuck upstream read must never delay a timeout,
    // and the dispatch guard still cancels the real transport.
    void iterator.return?.().catch(() => undefined);
  }
  options?.onOutcome?.({ model: request.model, promptTokens, completionTokens });
}
