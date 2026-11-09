/**
 * The single error-code catalog. Every API failure derives from this table:
 * HTTP status, default message, and retry policy live here and nowhere else.
 *
 * The rebuild collapses five former mirrors (the code list, the status map, the
 * domain-to-HTTP mapping table, the documentation table, and the QA gate) into
 * this one declaration.
 *
 * Retry policy is a three-valued judgement rather than a boolean, because
 * "retry" means two different things:
 * - `"yes"` — the identical request may be replayed immediately.
 * - `"after-delay"` — the caller must wait (honouring `retryAfter`) before
 *   retrying; replaying immediately loops.
 * - `"no"` — replaying the same request cannot succeed; the caller must change
 *   something first (re-read the document, fix validation, configure a
 *   provider).
 *
 * Two codes deliberately return `"no"` despite carrying a 503: replaying the
 * same request against the same instance cannot succeed for either, and
 * telling a client otherwise produces a hot retry loop.
 *
 * `Retry-After` is NOT declared per code. Whether a response carries the header
 * depends on the throw site, not on the code: `OPERATION_IN_FLIGHT` has six
 * construction points and only two of them know a delay. Declaring the header
 * on the code would either promise a value that four sites cannot supply, or
 * hide the one the retry route has shipped and tested. Callers read the header
 * when it is present and otherwise fall back to their own backoff.
 */

export type RetryPolicy = "yes" | "after-delay" | "no";

/**
 * What the caller must change before trying again. Separate from `retry`
 * because "retry the same request" and "fix something then retry" are different
 * instructions, and conflating them is how a client ends up hot-looping on a
 * 401.
 */
export type Remedy = "reauth" | "fix-request" | "reread" | "configure" | "none";

export interface ErrorDefinition {
  /** HTTP status rendered for this code. */
  readonly status: number;
  /** Fallback message when the throw site supplies none. */
  readonly defaultMessage: string;
  /** Whether, and how, the identical request may be retried. */
  readonly retry: RetryPolicy;
  /** What the caller must change for a later attempt to succeed. */
  readonly remedy: Remedy;
}

/**
 * Transport-layer failures are deliberately absent from this catalog. Fastify
 * answers malformed requests with its own codes and the envelope forwards them
 * verbatim: 413 `FST_ERR_CTP_BODY_TOO_LARGE` (the 1 MiB document body limit),
 * 415 `FST_ERR_CTP_INVALID_MEDIA_TYPE`, 400 `FST_ERR_CTP_INVALID_JSON_BODY`,
 * 400 `FST_ERR_CTP_INVALID_CONTENT_LENGTH`.
 *
 * In particular there is no `PAYLOAD_TOO_LARGE` code. Adding one here would
 * silently change a wire code that clients already match on, which the error
 * contract forbids: codes and statuses are stable, only messages may change.
 */
export const ERROR_CATALOG = {
  UNAUTHORIZED: {
    status: 401,
    defaultMessage: "Owner session required.",
    retry: "no",
    remedy: "reauth",
  },
  FORBIDDEN: {
    status: 403,
    defaultMessage: "The request is not permitted.",
    retry: "no",
    remedy: "reauth",
  },
  SETUP_TOKEN_INVALID: {
    status: 403,
    defaultMessage: "The first-start setup token is missing or invalid.",
    retry: "no",
    remedy: "fix-request",
  },
  CSRF_TOKEN_MISSING: {
    status: 403,
    defaultMessage: "The CSRF token is missing.",
    retry: "no",
    remedy: "reauth",
  },
  CSRF_TOKEN_INVALID: {
    status: 403,
    defaultMessage: "The CSRF token does not match the session.",
    retry: "no",
    remedy: "reauth",
  },
  RATE_LIMIT_EXCEEDED: {
    status: 429,
    defaultMessage: "Too many attempts; retry after the indicated delay.",
    retry: "after-delay",
    remedy: "none",
  },
  NOT_FOUND: {
    status: 404,
    defaultMessage: "The requested resource does not exist.",
    retry: "no",
    remedy: "none",
  },
  INVALID_OPERATION: {
    status: 422,
    defaultMessage: "The operation is not valid in the current state.",
    retry: "no",
    remedy: "reread",
  },
  PROVIDER_NOT_CONFIGURED: {
    status: 422,
    defaultMessage: "No text-generation provider is configured.",
    retry: "no",
    remedy: "configure",
  },
  EXPORT_CAPACITY_EXCEEDED: {
    status: 422,
    defaultMessage: "Export capacity exceeded.",
    retry: "no",
    remedy: "fix-request",
  },
  GENERATION_CAPACITY_EXCEEDED: {
    status: 422,
    defaultMessage: "Generation capacity exceeded.",
    retry: "no",
    remedy: "fix-request",
  },
  IMPORT_CAPACITY_EXCEEDED: {
    status: 422,
    defaultMessage: "Import capacity exceeded.",
    retry: "no",
    remedy: "fix-request",
  },
  STRUCTURE_CAPACITY_EXCEEDED: {
    status: 422,
    defaultMessage: "Structure capacity exceeded.",
    retry: "no",
    remedy: "fix-request",
  },
  VALIDATION_ERROR: {
    status: 422,
    defaultMessage: "Request validation failed.",
    retry: "no",
    remedy: "fix-request",
  },
  REVISION_CONFLICT: {
    status: 409,
    defaultMessage: "The document changed since the base revision.",
    retry: "no",
    remedy: "reread",
  },
  VOLUME_CONFLICT: {
    status: 409,
    defaultMessage: "A volume with this title already exists.",
    retry: "no",
    remedy: "fix-request",
  },
  SNAPSHOT_CONFLICT: {
    status: 409,
    defaultMessage: "The snapshot is referenced by a review or an export.",
    retry: "no",
    remedy: "none",
  },
  DOCUMENT_CONFLICT: {
    status: 409,
    defaultMessage: "The document conflicts with an existing one.",
    retry: "no",
    remedy: "fix-request",
  },
  OPERATION_IN_FLIGHT: {
    status: 409,
    defaultMessage: "An identical operation is already running; poll its status.",
    retry: "after-delay",
    remedy: "none",
  },
  OPERATION_CAPACITY_EXCEEDED: {
    status: 503,
    defaultMessage: "Too many operations are running; retry shortly.",
    retry: "after-delay",
    remedy: "none",
  },
  SERVICE_UNAVAILABLE: {
    status: 503,
    defaultMessage: "The service is temporarily unavailable.",
    retry: "no",
    remedy: "none",
  },
  INTERNAL_ERROR: {
    status: 500,
    defaultMessage: "An internal error occurred.",
    retry: "no",
    remedy: "none",
  },
} as const satisfies Record<string, ErrorDefinition>;

export type ErrorCode = keyof typeof ERROR_CATALOG;

/**
 * Codes whose default message throws away the only thing that makes the failure
 * actionable: which id, field, or provider failed.
 *
 * The throw site knows that detail; the catalog cannot. If `message` stayed
 * optional for these, forgetting it would silently downgrade
 * "Project not found: proj-1." to "The requested resource does not exist." —
 * and nothing in the type system would complain. Making it required here turns
 * that into a compile error at the throw site, which is the only place it can be
 * caught.
 */
export type ErrorCodeRequiringMessage =
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "INVALID_OPERATION"
  | "PROVIDER_NOT_CONFIGURED"
  | "VOLUME_CONFLICT"
  | "DOCUMENT_CONFLICT"
  | "OPERATION_IN_FLIGHT"
  | "SERVICE_UNAVAILABLE";

/** Codes that may fall back to the catalog sentence. */
export type ErrorCodeWithDefaultMessage = Exclude<ErrorCode, ErrorCodeRequiringMessage>;

/** Status for a code, derived — never declared twice. */
export function statusFor(code: ErrorCode): number {
  return ERROR_CATALOG[code].status;
}

/** Retry policy for a code. */
export function retryPolicyFor(code: ErrorCode): RetryPolicy {
  return ERROR_CATALOG[code].retry;
}

/** Every code, in a stable order for documentation and drift checks. */
export const ERROR_CODE_LIST: readonly ErrorCode[] = Object.keys(
  ERROR_CATALOG,
) as readonly ErrorCode[];

/** Remedy for an HTTP code. */
export function remedyFor(code: ErrorCode): Remedy {
  const definition: ErrorDefinition = ERROR_CATALOG[code];
  return definition.remedy;
}

export interface FrameErrorDefinition {
  readonly defaultMessage: string;
  readonly retry: RetryPolicy;
  readonly remedy: Remedy;
}

/**
 * Errors delivered inside an SSE `error` frame rather than an HTTP response.
 *
 * These live in a separate table on purpose. By the time one of them happens the
 * HTTP response has already committed as 200 and the headers are on the wire, so
 * there is no status to send. Folding them into `ERROR_CATALOG` would force a
 * fabricated status code that no client ever receives.
 */
export const FRAME_ERROR_CODES = {
  PROVIDER_FAILED: {
    defaultMessage: "The provider failed while streaming.",
    retry: "no",
    remedy: "reread",
  },
} as const satisfies Record<string, FrameErrorDefinition>;

export type FrameErrorCode = keyof typeof FRAME_ERROR_CODES;

export interface ErrorEnvelope {
  readonly error: {
    readonly code: string;
    readonly message: string;
    readonly details?: Record<string, unknown>;
  };
}
