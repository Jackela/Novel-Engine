import type { TextGenerationStreamOptions } from "../../application/ports/text_generation.js";
import {
  classifyTransportRejection,
  httpStatusFailure,
  malformedJsonFailure,
  type ProviderTransport,
  ProviderTransportError,
  redactCredentialAndTruncateResponseBody,
} from "./provider_http.js";

type JsonObject = Record<string, unknown>;

const EVENT_BOUNDARY = /\r?\n\r?\n/u;

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
  try {
    response = await transport(request.url, {
      method: "POST",
      headers: request.headers,
      body: request.body,
      signal: request.signal ?? null,
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
  for await (const payload of sseDataPayloads(body)) {
    if (payload.trim() === "[DONE]") break;
    const data = streamChunkObject(payload, request.context);
    const [prompt, completion] = extractUsage(data);
    if (prompt !== null) promptTokens = prompt;
    if (completion !== null) completionTokens = completion;
    const delta = extractDelta(data);
    if (delta !== undefined) yield delta;
  }
  options?.onOutcome?.({ model: request.model, promptTokens, completionTokens });
}
