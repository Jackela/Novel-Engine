import { TextGenerationCancelledError } from "../../application/ports/text_generation.js";
import {
  cancelProviderResponseBody,
  classifyTransportRejection,
  type ProviderTransport,
  ProviderTransportError,
  settleProviderCleanup,
  timeoutFailure,
} from "./provider_http.js";

export const MAX_PROVIDER_RESPONSE_BYTES = 8 * 1024 * 1024;
export const MAX_PROVIDER_STREAM_EVENT_BYTES = 1024 * 1024;

type ProviderBodyReader = ReturnType<ReadableStream<Uint8Array>["getReader"]>;
type ProviderBodyRead = Awaited<ReturnType<ProviderBodyReader["read"]>>;

/** One absolute outbound deadline shared by dispatch and every body read. */
export interface ProviderResponseDeadline {
  readonly signal: AbortSignal;
  readonly interrupted: Promise<never>;
  readonly timeoutSeconds: number;
  interrupt(failure: ProviderTransportError): ProviderTransportError;
  assertActive(): void;
  finish(): void;
}

export function startProviderResponseDeadline(
  context: string,
  timeoutSeconds: number,
  externalSignal?: AbortSignal | undefined,
): ProviderResponseDeadline {
  const guard = new AbortController();
  const timeout = timeoutFailure(context, timeoutSeconds);
  let firstFailure: Error | undefined;
  let rejectInterruption: ((failure: Error) => void) | undefined;
  const interrupted = new Promise<never>((_, reject) => {
    rejectInterruption = reject;
  });
  void interrupted.catch(() => undefined);
  const settle = (failure: Error): Error => {
    if (firstFailure !== undefined) return firstFailure;
    firstFailure = failure;
    rejectInterruption?.(failure);
    guard.abort();
    return failure;
  };
  const interrupt = (failure: ProviderTransportError): ProviderTransportError => {
    const authoritative = settle(failure);
    if (authoritative instanceof ProviderTransportError) return authoritative;
    throw authoritative;
  };
  let timer: ReturnType<typeof setTimeout> | undefined;
  timer = setTimeout(() => settle(timeout), timeoutSeconds * 1_000);
  const externalAbort = (): void => {
    settle(new TextGenerationCancelledError());
  };
  externalSignal?.addEventListener("abort", externalAbort, { once: true });
  if (externalSignal?.aborted === true) externalAbort();
  return {
    signal:
      externalSignal === undefined ? guard.signal : AbortSignal.any([externalSignal, guard.signal]),
    interrupted,
    timeoutSeconds,
    interrupt,
    assertActive: () => {
      if (firstFailure !== undefined) throw firstFailure;
    },
    finish: () => {
      if (timer !== undefined) clearTimeout(timer);
      timer = undefined;
      externalSignal?.removeEventListener("abort", externalAbort);
    },
  };
}

/** Race an in-progress boundary operation against the immutable deadline. */
export async function withinProviderDeadline<T>(
  pending: Promise<T>,
  deadline: ProviderResponseDeadline,
): Promise<T> {
  try {
    deadline.assertActive();
    const result = await Promise.race([pending, deadline.interrupted]);
    deadline.assertActive();
    return result;
  } catch (error) {
    pending.catch(() => undefined);
    throw error;
  }
}

/** Dispatch starts after the deadline and signal already exist. */
export async function dispatchProviderResponse(
  transport: ProviderTransport,
  url: string,
  init: RequestInit,
  context: string,
  deadline: ProviderResponseDeadline,
): Promise<Response | undefined> {
  let pending: Promise<Response | undefined> | undefined;
  try {
    deadline.assertActive();
    pending = transport(url, { ...init, signal: deadline.signal });
    return await withinProviderDeadline(pending, deadline);
  } catch (error) {
    if (pending !== undefined) {
      void pending
        .then(
          (response) => cancelProviderResponseBody(response?.body),
          () => undefined,
        )
        .catch(() => undefined);
    }
    const failure = classifyTransportRejection(error, context, deadline.timeoutSeconds);
    throw deadline.interrupt(failure);
  }
}

function responseSizeFailure(context: string): ProviderTransportError {
  return new ProviderTransportError(`${context}: response body exceeds 8 MiB limit.`);
}

export function streamEventSizeFailure(context: string): ProviderTransportError {
  return new ProviderTransportError(`${context}: stream event exceeds 1 MiB limit.`);
}

async function readBodyStep(
  pending: Promise<ProviderBodyRead>,
  context: string,
  deadline: ProviderResponseDeadline | undefined,
): Promise<ProviderBodyRead> {
  try {
    return deadline === undefined ? await pending : await withinProviderDeadline(pending, deadline);
  } catch (error) {
    const failure =
      error instanceof ProviderTransportError
        ? error
        : classifyTransportRejection(error, context, deadline?.timeoutSeconds ?? 0);
    throw deadline?.interrupt(failure) ?? failure;
  }
}

/**
 * Consume the original body exactly once, bounding raw bytes before decoding.
 * Only reader rejections are normalized; decoder/parser defects stay outside.
 */
export async function* boundedProviderBodyChunks(
  body: ReadableStream<Uint8Array>,
  context: string,
  deadline?: ProviderResponseDeadline | undefined,
): AsyncGenerator<Uint8Array, void, void> {
  const reader = body.getReader();
  let cancellation: Promise<void> | undefined;
  const cancelReader = (): void => {
    cancellation ??= settleProviderCleanup(() => reader.cancel());
  };
  deadline?.signal.addEventListener("abort", cancelReader, { once: true });
  if (deadline?.signal.aborted === true) cancelReader();
  let totalBytes = 0;
  try {
    while (true) {
      const step = await readBodyStep(reader.read(), context, deadline);
      if (step.done) break;
      const chunk = step.value;
      if (!(chunk instanceof Uint8Array)) {
        throw new TypeError("Provider response body yielded a non-byte chunk.");
      }
      totalBytes += chunk.byteLength;
      if (totalBytes > MAX_PROVIDER_RESPONSE_BYTES) {
        const failure = responseSizeFailure(context);
        throw deadline?.interrupt(failure) ?? failure;
      }
      yield chunk;
    }
  } finally {
    try {
      cancelReader();
      await cancellation;
    } finally {
      deadline?.signal.removeEventListener("abort", cancelReader);
      try {
        reader.releaseLock();
      } catch {
        // A raced read owns the lock until its already-handled rejection settles.
      }
    }
  }
}

/** Decode one bounded original response body without cloning it. */
export async function boundedProviderResponseText(
  response: Response,
  context: string,
  deadline?: ProviderResponseDeadline | undefined,
): Promise<string> {
  const body = response.body;
  if (body === null) return "";
  const decoder = new TextDecoder();
  let text = "";
  for await (const chunk of boundedProviderBodyChunks(body, context, deadline)) {
    text += decoder.decode(chunk, { stream: true });
  }
  return text + decoder.decode();
}
