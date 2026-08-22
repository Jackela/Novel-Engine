import type { FastifyError, FastifyInstance, FastifyReply } from "fastify";

import { InvalidOperationError } from "../../domain/exceptions.js";

/** Optional machine-readable payload carried inside the unified error envelope. */
export type ErrorEnvelopeDetails = Record<string, unknown>;

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
 * while the stack is logged under the request correlation id.
 */
export function registerErrorEnvelope(app: FastifyInstance): void {
  app.setErrorHandler((error: unknown, request, reply) => {
    if (error instanceof AppError) {
      sendEnvelope(reply, error.statusCode, error.code, error.message, error.details);
      return;
    }
    if (error instanceof InvalidOperationError) {
      sendEnvelope(reply, 422, "INVALID_OPERATION", error.message);
      return;
    }
    if (hasValidationErrors(error)) {
      sendEnvelope(
        reply,
        422,
        "VALIDATION_ERROR",
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
    sendEnvelope(reply, 500, "INTERNAL_ERROR", "An internal error occurred.", {
      error_id: errorId,
    });
  });

  app.setNotFoundHandler((request, reply) => {
    sendEnvelope(
      reply,
      404,
      "NOT_FOUND",
      `Route ${request.method} ${request.url} is not known to this API.`,
    );
  });
}
