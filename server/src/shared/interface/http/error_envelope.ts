import type { FastifyError, FastifyInstance, FastifyReply } from "fastify";

import { ERROR_CODES, type ErrorCode } from "../../domain/error_codes.js";
import { InvalidOperationError } from "../../domain/exceptions.js";

export type { ErrorCode };
export { ERROR_CODES };

/** Optional machine-readable payload carried inside the unified error envelope. */
export type ErrorEnvelopeDetails = Record<string, unknown>;

/** HTTP status the envelope renders for each catalog code. */
export const ERROR_HTTP_STATUS = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  CSRF_TOKEN_MISSING: 403,
  CSRF_TOKEN_INVALID: 403,
  RATE_LIMIT_EXCEEDED: 429,
  NOT_FOUND: 404,
  INVALID_OPERATION: 422,
  EXPORT_CAPACITY_EXCEEDED: 422,
  GENERATION_CAPACITY_EXCEEDED: 422,
  IMPORT_CAPACITY_EXCEEDED: 422,
  VALIDATION_ERROR: 422,
  REVISION_CONFLICT: 409,
  VOLUME_CONFLICT: 409,
  SNAPSHOT_CONFLICT: 409,
  DOCUMENT_CONFLICT: 409,
  OPERATION_IN_FLIGHT: 409,
  OPERATION_CAPACITY_EXCEEDED: 503,
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
  responseHeaders?: Readonly<Partial<Record<"retry-after", string>>>;
}

/**
 * The error type handlers throw for intentional API failures (409 revision
 * conflicts, 403 CSRF rejections, ...); the envelope renders it verbatim.
 */
export class AppError extends Error {
  readonly statusCode: number;
  readonly code: string;
  readonly details: ErrorEnvelopeDetails | undefined;
  readonly responseHeaders: Readonly<Partial<Record<"retry-after", string>>> | undefined;

  constructor(options: AppErrorOptions) {
    super(options.message);
    this.name = "AppError";
    this.statusCode = options.statusCode;
    this.code = options.code;
    this.details = options.details;
    this.responseHeaders = options.responseHeaders;
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
      if (error.responseHeaders?.["retry-after"] !== undefined) {
        reply.header("retry-after", error.responseHeaders["retry-after"]);
      }
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
