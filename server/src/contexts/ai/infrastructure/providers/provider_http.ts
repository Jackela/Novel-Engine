import {
  type ProviderStep,
  TextGenerationProviderError,
} from "../../application/ports/text_generation.js";

const RETRYABLE_HTTP_STATUSES = new Set([429, 500, 502, 503, 504]);
const MAX_PROVIDER_ATTEMPTS = 3;

/** Chapter generation calls must outlive the enclosing request timeout. */
export const GENERATION_TIMEOUT_FLOOR_SECONDS = 180;

/** Adapter fallback when neither composition nor options carry a timeout. */
export const DEFAULT_PROVIDER_TIMEOUT_SECONDS = 30;

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Structural usage token read; malformed or negative values stay null. */
export function usageToken(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
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

export function readableResponse(response: Response): Response {
  return typeof response.clone === "function" ? response.clone() : response;
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

export interface ProviderTransportErrorFields {
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

/** Cancel an untrusted failure stream without consuming it or exposing cleanup details. */
export async function discardHttpFailureResponse(
  context: string,
  response: Response,
): Promise<ProviderTransportError> {
  const failure = httpStatusFailure(context, response.status);
  const body = response.body;
  if (body === null || body === undefined) return failure;
  await body.cancel();
  return failure;
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

/** Chapter generation has a hard transport floor; editorial review keeps its base timeout. */
export function effectiveTimeoutSeconds(timeoutSeconds: number, step: ProviderStep): number {
  if (step === "chapter_draft" || step === "chapter_revision") {
    return Math.max(timeoutSeconds, GENERATION_TIMEOUT_FLOOR_SECONDS);
  }
  return timeoutSeconds;
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
