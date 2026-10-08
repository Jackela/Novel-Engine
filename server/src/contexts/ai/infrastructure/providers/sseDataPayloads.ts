import {
  boundedProviderBodyChunks,
  MAX_PROVIDER_STREAM_EVENT_BYTES,
  type ProviderResponseDeadline,
  streamEventSizeFailure,
} from "./provider_response_lifecycle.js";

const MAX_BOUNDARY_PREFIX_BYTES = 3;

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
    /** Report consumed raw bytes before decoding; observer errors propagate. */
    readonly onBytesReceived?: ((bytes: number) => void) | undefined;
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
    options?.onBytesReceived?.(chunk.byteLength);
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
