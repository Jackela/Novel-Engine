import type { FastifyReply, FastifyRequest, HookHandlerDoneFunction } from "fastify";

import {
  AppError,
  ERROR_CODES,
  ERROR_HTTP_STATUS,
} from "../../../../shared/interface/http/error_envelope.js";

const SUPPORTED_KEYS: ReadonlySet<string> = new Set(["title", "description", "settings"]);

function rawKeyValidationError(field: string, type: string, message: string): AppError {
  return new AppError({
    statusCode: ERROR_HTTP_STATUS[ERROR_CODES.VALIDATION_ERROR],
    code: ERROR_CODES.VALIDATION_ERROR,
    message: "Request validation failed.",
    details: { errors: [{ field, type, message }] },
  });
}

function validateRawFieldTypes(body: Record<string, unknown>): void {
  if (Object.hasOwn(body, "title") && typeof body.title !== "string") {
    throw rawKeyValidationError("title", "type", "must be string");
  }
  if (Object.hasOwn(body, "description") && typeof body.description !== "string") {
    throw rawKeyValidationError("description", "type", "must be string");
  }
  if (
    Object.hasOwn(body, "settings") &&
    (body.settings === null || typeof body.settings !== "object" || Array.isArray(body.settings))
  ) {
    throw rawKeyValidationError("settings", "type", "must be object");
  }
}

/** Preserve the closed PATCH contract before AJV can remove unknown properties. */
export function projectUpdateRawKeyGuard(
  request: FastifyRequest,
  _reply: FastifyReply,
  done: HookHandlerDoneFunction,
): void {
  const body: unknown = request.body;
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    done();
    return;
  }
  const keys = Object.keys(body);
  const unknown = keys.find((key) => !SUPPORTED_KEYS.has(key));
  if (unknown !== undefined) {
    throw rawKeyValidationError(unknown, "additionalProperties", "unknown field is not allowed");
  }
  if (!keys.some((key) => SUPPORTED_KEYS.has(key))) {
    throw rawKeyValidationError("(root)", "minProperties", "at least one field is required");
  }
  validateRawFieldTypes(body as Record<string, unknown>);
  done();
}
