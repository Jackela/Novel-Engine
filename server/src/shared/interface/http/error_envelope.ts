import type { FastifyError, FastifyInstance, FastifyReply } from "fastify";

import { InvalidOperationError } from "../../domain/exceptions.js";

/** Optional machine-readable payload carried inside the unified error envelope. */
export type ErrorEnvelopeDetails = Record<string, unknown>;

/**
 * The stable error-code catalog (SSOT): every SCREAMING_SNAKE code the
 * unified envelope can emit. Throw sites, schema enums, the OpenAPI
 * `ErrorEnvelope` component, and `docs/agents/error-codes.md` all derive
 * from these constants — never restate a code as a bare literal.
 */
export const ERROR_CODES = {
  UNAUTHORIZED: "UNAUTHORIZED",
  FORBIDDEN: "FORBIDDEN",
  CSRF_TOKEN_MISSING: "CSRF_TOKEN_MISSING",
  CSRF_TOKEN_INVALID: "CSRF_TOKEN_INVALID",
  RATE_LIMIT_EXCEEDED: "RATE_LIMIT_EXCEEDED",
  NOT_FOUND: "NOT_FOUND",
  INVALID_OPERATION: "INVALID_OPERATION",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  REVISION_CONFLICT: "REVISION_CONFLICT",
  VOLUME_CONFLICT: "VOLUME_CONFLICT",
  SNAPSHOT_CONFLICT: "SNAPSHOT_CONFLICT",
  DOCUMENT_CONFLICT: "DOCUMENT_CONFLICT",
  OPERATION_IN_FLIGHT: "OPERATION_IN_FLIGHT",
  SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
  INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

/** HTTP status the envelope renders for each catalog code. */
export const ERROR_HTTP_STATUS = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  CSRF_TOKEN_MISSING: 403,
  CSRF_TOKEN_INVALID: 403,
  RATE_LIMIT_EXCEEDED: 429,
  NOT_FOUND: 404,
  INVALID_OPERATION: 422,
  VALIDATION_ERROR: 422,
  REVISION_CONFLICT: 409,
  VOLUME_CONFLICT: 409,
  SNAPSHOT_CONFLICT: 409,
  DOCUMENT_CONFLICT: 409,
  OPERATION_IN_FLIGHT: 409,
  SERVICE_UNAVAILABLE: 503,
  INTERNAL_ERROR: 500,
} as const satisfies Record<ErrorCode, number>;

/** The single envelope channel for InvalidOperationError (status and code). */
export const INVALID_OPERATION_CODE = ERROR_CODES.INVALID_OPERATION;
export const INVALID_OPERATION_STATUS_CODE = ERROR_HTTP_STATUS[ERROR_CODES.INVALID_OPERATION];

export interface AppErrorOptions {
  statusCode: number;
  code: string;
  message: string;
  details?: ErrorEnvelopeDetails;
}

/**
 * The error type handlers throw for intentional API failures (409 revision
 * conflicts, 403 CSRF rejections, ...); the envelope renders it verbatim.
 */
export class AppError extends Error {
  readonly statusCode: number;
  readonly code: string;
  readonly details: ErrorEnvelopeDetails | undefined;

  constructor(options: AppErrorOptions) {
    super(options.message);
    this.name = "AppError";
    this.statusCode = options.statusCode;
    this.code = options.code;
    this.details = options.details;
  }
}

/** OpenAPI component name for the shared error envelope schema. */
export const ERROR_ENVELOPE_SCHEMA_ID = "ErrorEnvelope";

/**
 * The generic envelope shape shared by every non-conflict error response in
 * the OpenAPI document (`code` stays an open string so Fastify transport
 * codes such as FST_ERR_* keep passing through verbatim).
 */
export const errorEnvelopeSchema = {
  $id: ERROR_ENVELOPE_SCHEMA_ID,
  description:
    "Unified error envelope: every API failure renders as {error:{code,message,details?}}.",
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", description: "Stable code from the ERROR_CODES catalog." },
        message: { type: "string" },
        details: { type: "object", additionalProperties: true },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

/** Route response fragment referencing the shared `ErrorEnvelope` component. */
export const errorEnvelopeResponse = { $ref: ERROR_ENVELOPE_SCHEMA_ID } as const;

interface SerializedEnvelope {
  error: {
    code: string;
    message: string;
    details?: ErrorEnvelopeDetails;
  };
}

function sendEnvelope(
  reply: FastifyReply,
  statusCode: number,
  code: string,
  message: string,
  details?: ErrorEnvelopeDetails,
): void {
  const payload: SerializedEnvelope = { error: { code, message } };
  if (details !== undefined) {
    payload.error.details = details;
  }
  void reply.status(statusCode).send(payload);
}

interface FastifyValidationItem {
  instancePath?: string;
  keyword?: string;
  message?: string;
}

function hasValidationErrors(error: unknown): error is FastifyError {
  return error instanceof Error && Array.isArray((error as FastifyError).validation);
}

function validationDetails(error: FastifyError): ErrorEnvelopeDetails {
  const items = (error.validation ?? []) as FastifyValidationItem[];
  return {
    errors: items.map((item) => ({
      field: (item.instancePath ?? "").replace(/^\//, "") || "(root)",
      message: item.message ?? "value is invalid",
      type: item.keyword ?? "invalid",
    })),
  };
}

/**
 * Install the unified error envelope: every API failure renders as
 * {"error":{code,message,details?}} and the {"detail": ...} shape never
 * appears. Unhandled failures stay opaque (INTERNAL_ERROR plus an error_id)
 * while the stack is logged under the request correlation id. Also registers
 * the shared `ErrorEnvelope` component schema so route response declarations
 * can reference one envelope shape.
 */
export function registerErrorEnvelope(app: FastifyInstance): void {
  app.addSchema(errorEnvelopeSchema);
  app.setErrorHandler((error: unknown, request, reply) => {
    if (error instanceof AppError) {
      sendEnvelope(reply, error.statusCode, error.code, error.message, error.details);
      return;
    }
    if (error instanceof InvalidOperationError) {
      sendEnvelope(reply, INVALID_OPERATION_STATUS_CODE, INVALID_OPERATION_CODE, error.message);
      return;
    }
    if (hasValidationErrors(error)) {
      sendEnvelope(
        reply,
        422,
        ERROR_CODES.VALIDATION_ERROR,
        "Request validation failed.",
        validationDetails(error),
      );
      return;
    }
    const fastifyError = error as FastifyError;
    if (
      typeof fastifyError.statusCode === "number" &&
      fastifyError.statusCode >= 400 &&
      fastifyError.statusCode < 500 &&
      typeof fastifyError.code === "string" &&
      fastifyError.code.startsWith("FST_ERR")
    ) {
      sendEnvelope(reply, fastifyError.statusCode, fastifyError.code, fastifyError.message);
      return;
    }
    const errorId = request.id;
    request.log.error({ err: error, errorId }, "unhandled error while serving request");
    sendEnvelope(reply, 500, ERROR_CODES.INTERNAL_ERROR, "An internal error occurred.", {
      error_id: errorId,
    });
  });

  app.setNotFoundHandler((request, reply) => {
    sendEnvelope(
      reply,
      404,
      ERROR_CODES.NOT_FOUND,
      `Route ${request.method} ${request.url} is not known to this API.`,
    );
  });
}
