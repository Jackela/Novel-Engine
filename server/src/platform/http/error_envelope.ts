/**
 * The unified error envelope for the rebuilt API.
 *
 * Difference from the previous implementation: an `AppError` no longer carries
 * its own status code. It carries a catalog code, and the status is derived
 * from `ERROR_CATALOG`. That removes the class of bug where a throw site passed
 * 409 for a code documented as 422.
 *
 * Guarantees:
 * - Every failure renders as `{ error: { code, message, details? } }`.
 * - Validation failures become VALIDATION_ERROR with per-field details.
 * - Unknown failures become INTERNAL_ERROR with an `error_id`, and the stack is
 *   logged under that id — never sent to the client.
 * - Fastify transport errors (FST_ERR_*) keep their own status and code, since
 *   they describe request framing rather than application state.
 */

import type { FastifyError, FastifyInstance, FastifyReply } from "fastify";

import {
  ERROR_CATALOG,
  type ErrorCode,
  type ErrorCodeRequiringMessage,
  type ErrorCodeWithDefaultMessage,
  type ErrorEnvelope,
} from "../../contracts/errors.js";

export interface AppErrorOptions {
  readonly details?: Record<string, unknown>;
  /** Overrides the catalog default; use only when more specific. */
  readonly message?: string;
  /**
   * Sets `Retry-After` on **any** status, not only 429/503.
   *
   * A keyed-retry 409 carries it too, and that header is what makes the 409
   * actionable; the implementation deliberately does not branch on status. The
   * decision to send it belongs to the throw site — readers use it when present
   * and fall back to their own backoff when absent. "Fixing" the status check
   * here would silently drop the header from the retry route.
   */
  readonly retryAfterSeconds?: number;
}

/** An intentional API failure identified by its catalog code. */
export class AppError extends Error {
  readonly code: ErrorCode;
  readonly details: Record<string, unknown> | undefined;
  readonly retryAfterSeconds: number | undefined;

  /**
   * Codes whose catalog sentence omits the failing id or field require a
   * message. Overloading (rather than a runtime check) puts the requirement at
   * the call site, where the detail actually exists.
   */
  constructor(
    code: ErrorCodeRequiringMessage,
    options: AppErrorOptions & { readonly message: string },
  );
  constructor(code: ErrorCodeWithDefaultMessage, options?: AppErrorOptions);
  constructor(code: ErrorCode, options: AppErrorOptions = {}) {
    super(options.message ?? ERROR_CATALOG[code].defaultMessage);
    this.name = "AppError";
    this.code = code;
    this.details = options.details;
    this.retryAfterSeconds = options.retryAfterSeconds;
  }

  get statusCode(): number {
    return ERROR_CATALOG[this.code].status;
  }

  /**
   * Build an error that must carry `Retry-After`.
   *
   * The delay is a required argument on purpose: a code whose policy is
   * `after-delay` tells the client to wait, and a response that says "wait"
   * without saying how long forces it to guess. Only the throw sites that
   * actually know the delay call this; the others throw the plain constructor
   * and the client falls back to its own backoff.
   */
  static afterDelay(
    code: ErrorCodeRequiringMessage,
    seconds: number,
    options: AppErrorOptions & { readonly message: string },
  ): AppError;
  static afterDelay(
    code: ErrorCodeWithDefaultMessage,
    seconds: number,
    options?: Omit<AppErrorOptions, "retryAfterSeconds">,
  ): AppError;
  static afterDelay(
    code: ErrorCode,
    seconds: number,
    options: Omit<AppErrorOptions, "retryAfterSeconds"> = {},
  ): AppError {
    // The assertion is confined to the implementation: both overloads above
    // already force a message for the codes that need one.
    return new AppError(code as ErrorCodeWithDefaultMessage, {
      ...options,
      retryAfterSeconds: seconds,
    });
  }
}

function send(
  reply: FastifyReply,
  status: number,
  code: string,
  message: string,
  details?: Record<string, unknown>,
): void {
  const payload: ErrorEnvelope = details === undefined
    ? { error: { code, message } }
    : { error: { code, message, details } };
  void reply.status(status).send(payload);
}

interface ValidationItem {
  readonly instancePath?: string;
  readonly keyword?: string;
  readonly message?: string;
}

function isValidationFailure(error: unknown): error is FastifyError & { validation: ValidationItem[] } {
  return error instanceof Error && Array.isArray((error as FastifyError).validation);
}

function validationDetails(items: readonly ValidationItem[]): Record<string, unknown> {
  return {
    errors: items.map((item) => ({
      field: (item.instancePath ?? "").replace(/^\//, "") || "(root)",
      message: item.message ?? "value is invalid",
      type: item.keyword ?? "invalid",
    })),
  };
}

/** True for Fastify's own transport errors, which carry a meaningful status. */
function isTransportError(error: FastifyError): boolean {
  return (
    typeof error.statusCode === "number" &&
    error.statusCode >= 400 &&
    error.statusCode < 500 &&
    typeof error.code === "string" &&
    error.code.startsWith("FST_ERR")
  );
}

/** Install the envelope on an app instance. Call once, in the composition root. */
export function registerErrorEnvelope(app: FastifyInstance): void {
  app.setErrorHandler((error: unknown, request, reply) => {
    if (error instanceof AppError) {
      if (error.retryAfterSeconds !== undefined) {
        void reply.header("retry-after", String(error.retryAfterSeconds));
      }
      send(reply, error.statusCode, error.code, error.message, error.details);
      return;
    }
    if (isValidationFailure(error)) {
      const definition = ERROR_CATALOG.VALIDATION_ERROR;
      send(reply, definition.status, "VALIDATION_ERROR", definition.defaultMessage, validationDetails(error.validation));
      return;
    }
    const candidate = error as FastifyError;
    if (isTransportError(candidate)) {
      send(reply, candidate.statusCode as number, candidate.code, candidate.message);
      return;
    }
    const errorId = request.id;
    request.log.error({ err: error, errorId }, "unhandled error while serving request");
    const definition = ERROR_CATALOG.INTERNAL_ERROR;
    send(reply, definition.status, "INTERNAL_ERROR", definition.defaultMessage, { error_id: errorId });
  });

  app.setNotFoundHandler((request, reply) => {
    const definition = ERROR_CATALOG.NOT_FOUND;
    send(
      reply,
      definition.status,
      "NOT_FOUND",
      `Route ${request.method} ${request.url} is not known to this API.`,
    );
  });
}
