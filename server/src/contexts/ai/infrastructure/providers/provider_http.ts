import {
  isSafeUsageToken,
  type ProviderStep,
  TextGenerationProviderError,
  type TextGenerationStreamOptions,
} from "../../application/ports/text_generation.js";

const RETRYABLE_HTTP_STATUSES = new Set([429, 500, 502, 503, 504]);
const MAX_PROVIDER_ATTEMPTS = 3;
const PROVIDER_CLEANUP_GRACE_MS = 1_000;

/**
 * Whole-manuscript provider calls (draft, revision, editorial review, lore
 * extraction) must outlive the enclosing request timeout: the default 30s
 * transport deadline cuts real work on any non-trivial manuscript.
 */
export const LONG_FORM_TIMEOUT_FLOOR_SECONDS = 180;

/** Adapter fallback when neither composition nor options carry a timeout. */
export const DEFAULT_PROVIDER_TIMEOUT_SECONDS = 30;

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Structural usage token read; inexact or malformed values stay null. */
export function usageToken(value: unknown): number | null {
  return isSafeUsageToken(value) ? value : null;
}

export function isResponseLike(value: unknown): value is Response {
  if (!isJsonObject(value)) return false;
  return (
    typeof value.ok === "boolean" &&
    typeof value.status === "number" &&
    typeof value.text === "function" &&
    typeof value.json === "function"
  );
}

/** Trim the configured key; the provider label keeps each error message verbatim. */
export function requiredApiKey(value: string, providerLabel: string): string {
  const apiKey = value.trim();
  if (apiKey === "") {
    throw new TextGenerationProviderError(`${providerLabel} API key is required`);
  }
  return apiKey;
}

export function normalizedTimeoutSeconds(
  value: number | undefined,
  fallbackSeconds: number,
): number {
  if (value === undefined || !Number.isFinite(value) || value <= 0) {
    return fallbackSeconds;
  }
  return value;
}

interface ProviderTransportErrorFields {
  readonly status?: number | undefined;
  readonly timedOut?: boolean | undefined;
  readonly malformedJson?: boolean | undefined;
}

/**
 * A normalized transport failure with the facts needed to make retry decisions.
 * It remains a provider error so the proposal workflow records it as a job error.
 */
export class ProviderTransportError extends TextGenerationProviderError {
  readonly status: number | undefined;
  readonly timedOut: boolean;
  readonly malformedJson: boolean;
  readonly retryable: boolean;

  constructor(message: string, fields: ProviderTransportErrorFields = {}) {
    super(message);
    this.name = "ProviderTransportError";
    this.status = fields.status;
    this.timedOut = fields.timedOut === true;
    this.malformedJson = fields.malformedJson === true;
    this.retryable =
      this.timedOut ||
      this.malformedJson ||
      (this.status !== undefined && RETRYABLE_HTTP_STATUSES.has(this.status));
  }
}

export interface ProviderRetryPolicy {
  readonly maxAttempts?: number | undefined;
  readonly delayMs?: number | undefined;
  readonly sleep?: ((delayMs: number) => Promise<void>) | undefined;
}

/** Injectable fetch boundary; adapters never create transport singletons at import time. */
export type ProviderTransport = (url: string, init?: RequestInit) => Promise<Response | undefined>;

/** The shared provider policy: three total attempts, with one second between retries. */
export const DEFAULT_PROVIDER_RETRY_POLICY: ProviderRetryPolicy = {
  maxAttempts: MAX_PROVIDER_ATTEMPTS,
  delayMs: 1_000,
};

function defaultSleep(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}

function positiveAttemptCount(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value)) {
    return MAX_PROVIDER_ATTEMPTS;
  }
  return Math.min(MAX_PROVIDER_ATTEMPTS, Math.max(1, Math.floor(value)));
}

function nonNegativeDelay(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value)) {
    return DEFAULT_PROVIDER_RETRY_POLICY.delayMs ?? 1_000;
  }
  return Math.max(0, value);
}

/** Retry only the normalized provider failures whose structured facts allow it. */
export function providerFailureIsRetryable(failure: ProviderTransportError): boolean {
  return failure.retryable;
}

async function attemptWithRetries<T>(
  attemptsRemaining: number,
  delayMs: number,
  sleep: (delay: number) => Promise<void>,
  operation: () => Promise<T>,
): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    if (!(error instanceof ProviderTransportError) || !providerFailureIsRetryable(error)) {
      throw error;
    }
    if (attemptsRemaining === 1) {
      throw error;
    }
    await sleep(delayMs);
    return attemptWithRetries(attemptsRemaining - 1, delayMs, sleep, operation);
  }
}

/** Run one provider operation with the bounded retry policy. */
export function runWithRetryPolicy<T>(
  policy: ProviderRetryPolicy,
  operation: () => Promise<T>,
): Promise<T> {
  return attemptWithRetries(
    positiveAttemptCount(policy.maxAttempts),
    nonNegativeDelay(policy.delayMs),
    policy.sleep ?? defaultSleep,
    operation,
  );
}

/** Normalize a non-success HTTP response without using its body to choose retry behavior. */
export function httpStatusFailure(context: string, status: number): ProviderTransportError {
  return new ProviderTransportError(`${context}: provider returned HTTP ${status}.`, { status });
}

/** Await cleanup without allowing rejection or a hostile thenable to replace request truth. */
export async function settleProviderCleanup(start: () => Promise<unknown>): Promise<void> {
  let cleanup: Promise<unknown>;
  try {
    cleanup = Promise.resolve(start());
  } catch {
    return;
  }
  void cleanup.catch(() => undefined);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const graceElapsed = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, PROVIDER_CLEANUP_GRACE_MS);
  });
  try {
    await Promise.race([cleanup.catch(() => undefined), graceElapsed]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

/** Cancel one response body within the shared bounded cleanup grace. */
export function cancelProviderResponseBody(
  body: ReadableStream<Uint8Array> | null | undefined,
): Promise<void> {
  return body === null || body === undefined
    ? Promise.resolve()
    : settleProviderCleanup(() => body.cancel());
}

type ProviderFailureRegistrar = (failure: ProviderTransportError) => ProviderTransportError;

/** Register HTTP status first, then cancel its untrusted body without consuming it. */
export async function discardHttpFailureResponse(
  context: string,
  response: Response,
  registerFailure: ProviderFailureRegistrar = (failure) => failure,
): Promise<ProviderTransportError> {
  let authoritative: unknown;
  try {
    authoritative = registerFailure(httpStatusFailure(context, response.status));
  } catch (error) {
    authoritative = error;
  }
  await cancelProviderResponseBody(response.body);
  if (authoritative instanceof ProviderTransportError) return authoritative;
  throw authoritative;
}

/** Normalize a response that failed JSON-object parsing. */
export function malformedJsonFailure(context: string): ProviderTransportError {
  return new ProviderTransportError(`${context}: invalid JSON response.`, { malformedJson: true });
}

/** Normalize an elapsed outbound transport deadline. */
export function timeoutFailure(context: string, timeoutSeconds: number): ProviderTransportError {
  return new ProviderTransportError(`${context} timed out after ${timeoutSeconds}s.`, {
    timedOut: true,
  });
}

/** A provider-reported failure payload embedded in a 200 SSE stream (DR-026). */
export interface ProviderStreamFailure {
  readonly message: string;
  readonly code: string;
}

/** Normalize an in-stream provider failure; stable phrasing feeds the job error. */
export function providerStreamFailure(
  context: string,
  failure: ProviderStreamFailure,
): ProviderTransportError {
  return new ProviderTransportError(
    `${context}: provider reported ${failure.message} (code ${failure.code})`,
  );
}

function errorPayloadCode(error: Record<string, unknown>): string {
  for (const candidate of [error.code, error.type]) {
    if (typeof candidate === "string" && candidate.trim() !== "") return candidate.trim();
    if (typeof candidate === "number" && Number.isFinite(candidate)) return String(candidate);
  }
  return "unknown";
}

function errorPayloadFailure(error: unknown): ProviderStreamFailure | undefined {
  if (!isJsonObject(error)) return undefined;
  const message = typeof error.message === "string" ? error.message.trim() : "";
  return message === "" ? undefined : { message, code: errorPayloadCode(error) };
}

/**
 * Recognize compatible error payloads and failed/incomplete Responses events.
 * An adverse Responses event fails immediately, even without readable error
 * detail; a later DONE marker cannot turn that outcome into success.
 */
export function openAiCompatibleStreamFailure(
  data: Record<string, unknown>,
): ProviderStreamFailure | undefined {
  if (data.type !== "response.failed" && data.type !== "response.incomplete") {
    return errorPayloadFailure(data.error);
  }
  const response = isJsonObject(data.response) ? data.response : {};
  const failure = errorPayloadFailure(response.error);
  if (failure !== undefined) return failure;
  const details = response.incomplete_details;
  const reason =
    isJsonObject(details) && typeof details.reason === "string" ? details.reason.trim() : "";
  return {
    code: data.type,
    message:
      data.type === "response.failed"
        ? "response failed"
        : `response incomplete${reason === "" ? "" : `: ${reason}`}`,
  };
}

/**
 * Engine options for the streaming path: the application stream options plus
 * the adapter's in-stream failure detector. The engine runs the detector on
 * every parsed frame before extraction; a returned error is raised immediately
 * and never retried, because a frame has already flowed into the consumer.
 */
export interface ProviderStreamOptions extends TextGenerationStreamOptions {
  readonly extractStreamFailure?:
    | ((chunk: Record<string, unknown>) => ProviderTransportError | undefined)
    | undefined;
  /** Recognize protocol completion without skipping trailing usage or errors. */
  readonly isTerminalChunk?: ((chunk: Record<string, unknown>) => boolean) | undefined;
}

/**
 * Long-form steps hand the provider a whole manuscript; every step of the
 * closed vocabulary is one today, so the floor applies to all of them. Keep
 * the list explicit: a future short-lived step must not inherit a floor it
 * does not need.
 */
const LONG_FORM_STEPS: ReadonlySet<ProviderStep> = new Set<ProviderStep>([
  "chapter_draft",
  "chapter_revision",
  "editorial_review",
  "lore_extract",
]);

/** Long-form steps have a hard transport floor; every other step keeps its base timeout. */
export function effectiveTimeoutSeconds(timeoutSeconds: number, step: ProviderStep): number {
  return LONG_FORM_STEPS.has(step)
    ? Math.max(timeoutSeconds, LONG_FORM_TIMEOUT_FLOOR_SECONDS)
    : timeoutSeconds;
}

function rejectionName(rejection: unknown): string | undefined {
  if (
    typeof rejection === "object" &&
    rejection !== null &&
    "name" in rejection &&
    typeof rejection.name === "string"
  ) {
    return rejection.name;
  }
  return undefined;
}

/**
 * Convert only known fetch-boundary rejections. Message text is display-only;
 * retry eligibility is always derived from structured error fields.
 */
export function classifyTransportRejection(
  rejection: unknown,
  context: string,
  timeoutSeconds: number,
): ProviderTransportError {
  if (rejection instanceof ProviderTransportError) {
    return rejection;
  }
  const name = rejectionName(rejection);
  if (name === "AbortError" || name === "TimeoutError") {
    return timeoutFailure(context, timeoutSeconds);
  }
  if (rejection instanceof TypeError) {
    // Fetch implementations can include request diagnostics in TypeError.message,
    // while a failed job persists this text, so only the trusted context is retained.
    return new ProviderTransportError(`${context}: transport request failed.`);
  }
  throw rejection;
}
